import hashlib
import json
import requests
import re

import tile_library.basic_functions as basic_fns
from tile_library.constants import CHR_PATH_LENGTHS, CHR_OTHER, TAG_LENGTH, \
    NUM_HEX_INDEXES_FOR_VERSION, NUM_HEX_INDEXES_FOR_PATH, NUM_HEX_INDEXES_FOR_STEP, \
    NUM_HEX_INDEXES_FOR_VARIANT_VALUE, LANTERN_NAME_FORMAT_STRING
from errors import TileLibraryValidationError

position_length = NUM_HEX_INDEXES_FOR_VERSION + NUM_HEX_INDEXES_FOR_PATH + NUM_HEX_INDEXES_FOR_STEP
def validate_json(text):
    try:
        json.loads(text)
    except ValueError:
        raise TileLibraryValidationError("Expects json-formatted text")

def validate_tile_position_int(tile_position_int):
    if tile_position_int < 0:
        raise TileLibraryValidationError({'tile_position_int':"integer must be positive"})
    v='f'*(NUM_HEX_INDEXES_FOR_VERSION)
    p='f'*(NUM_HEX_INDEXES_FOR_PATH)
    s='f'*(NUM_HEX_INDEXES_FOR_STEP)
    max_tile_position = int(v+p+s, 16)
    if tile_position_int > max_tile_position:
        raise TileLibraryValidationError({'tile_position_int':"tile position int must be smaller than or equal to '%s.%s.%s'" % (v,p,s)})

def validate_tile_variant_int(tile_variant_int):
    if tile_variant_int < 0:
        raise TileLibraryValidationError({'tile_variant_int':"integer must be positive"})
    v='f'*(NUM_HEX_INDEXES_FOR_VERSION)
    p='f'*(NUM_HEX_INDEXES_FOR_PATH)
    s='f'*(NUM_HEX_INDEXES_FOR_STEP)
    vv='f'*(NUM_HEX_INDEXES_FOR_VARIANT_VALUE)
    max_tile_variant = int(v+p+s+vv, 16)
    if tile_variant_int > max_tile_variant:
        raise TileLibraryValidationError({'tile_variant_int':"tile variant int must be smaller than or equal to '%s.%s.%s.%s'" % (v,p,s,vv)})

def validate_tag(tag):
    if tag.lower() != tag:
        raise TileLibraryValidationError("Tag must be lowercase")
    if len(tag) != TAG_LENGTH and len(tag) != 0:
        raise TileLibraryValidationError("Tag length must be equal to the set TAG_LENGTH or must be empty")

def validate_tile_position(tile_position_int, is_start_of_path, is_end_of_path, start_tag, end_tag):
    VALIDATION_ERRORS = {}
    version, path, step = basic_fns.get_position_ints_from_position_int(tile_position_int)
    if step == 0:
        if not is_start_of_path:
            VALIDATION_ERRORS['tile_position_int-is_start_of_path'] = "If step is 0, is_start_of_path should be True"
    else:
        if is_start_of_path:
            VALIDATION_ERRORS['tile_position_int-is_start_of_path'] = "If step is not 0, is_start_of_path should be False"
    try:
        validate_tag(start_tag)
    except TileLibraryValidationError as e:
        VALIDATION_ERRORS['start_tag'] = e.value
    try:
        validate_tag(end_tag)
    except TileLibraryValidationError as e:
        VALIDATION_ERRORS['end_tag'] = e.value
    if is_start_of_path:
        if start_tag != '':
            VALIDATION_ERRORS['start_tag-is_start_of_path'] = "If is_start_of_path, start_tag should be empty"
    else:
        if start_tag == '':
            VALIDATION_ERRORS['start_tag-is_start_of_path'] = "If not is_start_of_path, start_tag should not be empty"
    if is_end_of_path:
        if end_tag != '':
            VALIDATION_ERRORS['end_tag-is_end_of_path'] = "If is_end_of_path, end_tag should be empty"
    else:
        if end_tag == '':
            VALIDATION_ERRORS['end_tag-is_end_of_path'] = "If not is_end_of_path, end_tag should not be empty"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_num_spanning_tiles(num_spanning):
    if num_spanning < 1:
        raise TileLibraryValidationError("num positions spanned must be greater than or equal to 1")

def validate_spanning_tile(tile_position_one, tile_position_two, num_positions_spanned):
    validate_tile_position_int(tile_position_one)
    validate_tile_position_int(tile_position_two)
    #If these throw an error, I want it to propogate.
    tile1_path_version, tile1_path, tile1_step = basic_fns.get_position_ints_from_position_int(tile_position_one)
    tile2_path_version, tile2_path, tile2_step = basic_fns.get_position_ints_from_position_int(tile_position_two)
    if tile1_path_version != tile2_path_version:
        raise TileLibraryValidationError({'spanning_tile_error':'starting and ending tiles cross path versions'})
    if tile1_path != tile2_path:
        raise TileLibraryValidationError({'spanning_tile_error':'starting and ending tiles cross paths'})
    if abs(tile2_step - tile1_step) != num_positions_spanned-1:
        raise TileLibraryValidationError({'spanning_tile_error':'number of steps spanned (from tile position integers and reported) do not match'})

def validate_tile_variant(tile_position_int, tile_variant_int, variant_value, sequence, seq_length, seq_md5sum, start_tag, end_tag, is_start_of_path, is_end_of_path):
    acceptable_seq_length = TAG_LENGTH*2
    if is_start_of_path:
        acceptable_seq_length -= TAG_LENGTH
    if is_end_of_path:
        acceptable_seq_length -= TAG_LENGTH
    VALIDATION_ERRORS = {}
    #If these throw an error, I want it to propogate.
    validate_tile_position_int(tile_position_int)
    validate_tile_variant_int(tile_variant_int)
    tile_path_version, tile_path, tile_step = basic_fns.get_position_ints_from_position_int(tile_position_int)
    variant_path_version, variant_path, variant_step, variant_val = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_variant_int)
    if tile_path_version != variant_path_version:
        VALIDATION_ERRORS['version_mismatch'] = "tile variant path version and tile position path version must be equal"
    if tile_path != variant_path:
        VALIDATION_ERRORS['path_mismatch'] = "tile variant path and tile position path must be equal"
    if tile_step != variant_step:
        VALIDATION_ERRORS['step_mismatch'] = "tile variant step and tile position step must be equal"
    if variant_val != variant_value:
        VALIDATION_ERRORS['variant_value_mismatch'] = "tile variant value and input variant value must be equal"
    if seq_length != len(sequence):
        VALIDATION_ERRORS['length_mismatch'] = "length must be the length of the sequence"
    if sequence.lower() != sequence:
        VALIDATION_ERRORS['sequence'] = "Sequence must be entirely lowercase"
    digestor = hashlib.new('md5', sequence)
    if digestor.hexdigest() != seq_md5sum:
        VALIDATION_ERRORS['md5sum-sequence'] = "md5sum is not actually md5sum of sequence"
    if len(sequence) < acceptable_seq_length:
        VALIDATION_ERRORS['sequence_malformed'] = "Sequence is not long enough - the tags overlap"
    if sequence[:TAG_LENGTH] != start_tag:
        VALIDATION_ERRORS['start_tag-sequence'] = "Sequence does not start with the given start tag"
    if sequence[-TAG_LENGTH:] != end_tag:
        VALIDATION_ERRORS['end_tag-sequence'] = "Sequence does not end with the given end tag"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_locus(chromosome_int, tile_position_int, TAG_LENGTH, tile_sequence_length, begin_int, end_int):
    VALIDATION_ERRORS = {}
    version, path, step = basic_fns.get_position_ints_from_position_int(tile_position_int)
    if path not in range(CHR_PATH_LENGTHS[chromosome_int-1], CHR_PATH_LENGTHS[chromosome_int]):
        VALIDATION_ERRORS['chromosome_int-tile_position'] = "Path %i is not in chromosome %i, based on CHR_PATH_LENGTHS" % (path,chromosome_int)
    if end_int <= begin_int:
        VALIDATION_ERRORS['malformed_locus'] = "end_int must be strictly larger than begin_int"
    if tile_sequence_length != end_int - begin_int:
        VALIDATION_ERRORS['tile_length_locus_mismatch'] = "Sequence length must be the same length specified by the loci"
    if end_int - begin_int < TAG_LENGTH*2:
        VALIDATION_ERRORS['short_locus'] = "the distance between begin_int and end_int must be greater than twice the TAG_LENGTH"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_lantern_translation(lantern_name, tile_variant_int):
    VALIDATION_ERRORS = {}
    #If these throw an error, I want it to propogate.
    #Check that lantern_name doesn't have spanning tile notation
    matching = re.match(LANTERN_NAME_FORMAT_STRING, lantern_name)
    if matching.group(2) != None:
        VALIDATION_ERRORS['lantern_name'] = "lantern_name cannot have spanning tile notation"
    tile_position_int = basic_fns.get_position_from_cgf_string(lantern_name)
    validate_tile_variant_int(tile_variant_int)
    tile_path_version, tile_path, tile_step = basic_fns.get_position_ints_from_position_int(tile_position_int)
    variant_path_version, variant_path, variant_step, variant_val = basic_fns.get_tile_variant_ints_from_tile_variant_int(tile_variant_int)
    if tile_path_version != variant_path_version:
        VALIDATION_ERRORS['version_mismatch'] = "tile variant path version and tile position path version must be equal"
    if tile_path != variant_path:
        VALIDATION_ERRORS['path_mismatch'] = "tile variant path and tile position path must be equal"
    if tile_step != variant_step:
        VALIDATION_ERRORS['step_mismatch'] = "tile variant step and tile position step must be equal"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_lantern_translation_outside_database(tile_library_host, tile_library_path):
    try:
        r = requests.get("http://%s%s" % (tile_library_host, tile_library_path), timeout=1)
    except Exception as e:
        raise TileLibraryValidationError({'tile_library_host':str(e)})
    if r.status_code != requests.codes.ok:
        raise TileLibraryValidationError({'tile_library_int-tile_library_host':r.text})

def validate_reference_bases(reference_seq, start, end, reference_bases):
    """
        check genome variant reference bases are the bases in the reference sequence
    """
    if reference_seq[start:end].upper() != reference_bases.strip('-').upper():
        raise TileLibraryValidationError(
            {'reference_bases':"Reference bases (%s) do not match bases in reference tile variant (%s)" % (reference_bases, reference_seq[start:end])}
        )
def validate_reference_versus_alternate_bases(ref_bases, alt_bases):
    if ref_bases.upper() == alt_bases.upper():
        raise TileLibraryValidationError(
            {'reference_bases-alternate_bases':"Reference bases (%s) are the same as alternate bases (%s)" % (ref_bases, alt_bases)}
        )

def validate_same_chromosome(locus_chrom_int, variant_chrom_int, locus_chrom_name, variant_chrom_name):
    """
        check genome variant chromosome is the same as the locus chromosome
    """
    VALIDATION_ERRORS = {}
    if locus_chrom_int != variant_chrom_int:
        VALIDATION_ERRORS['chromosome_int'] = 'Locus for tile variant is not in chromosome %i' % (variant_chrom_int)
    if locus_chrom_name != variant_chrom_name:
        VALIDATION_ERRORS['alternate_chromosome_name'] = "Locus for tile variant is not in chromosome %s" % (variant_chrom_name)
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_tile_variant_loci_encompass_genome_variant_loci(genome_var_start_int, genome_var_end_int, tile_var_start_int, tile_var_end_int, tile_var_is_at_start, tile_var_is_at_end):
    """
        check genome variant loci are within tile variant loci
    """
    VALIDATION_ERRORS = {}
    acceptable_start_position = tile_var_start_int+TAG_LENGTH
    start_msg = "%s is in the start tag or before the locus"
    if tile_var_is_at_start:
        acceptable_start_position -= TAG_LENGTH
        start_msg = "%s is before the locus"
    acceptable_end_position = tile_var_end_int-TAG_LENGTH
    end_msg = "%s is in the end tag or after the locus"
    if tile_var_is_at_end:
        acceptable_end_position += TAG_LENGTH
        end_msg = "%s is after the locus"
    if genome_var_start_int < acceptable_start_position:
        VALIDATION_ERRORS['genome_variant.start_int'] = start_msg % "start_int"
    if genome_var_start_int > acceptable_end_position:
        VALIDATION_ERRORS['genome_variant.start_int'] = end_msg % "start_int"
    if genome_var_end_int < acceptable_start_position:
        VALIDATION_ERRORS['genome_variant.end_int'] = start_msg % "end_int"
    if genome_var_end_int > acceptable_end_position:
        VALIDATION_ERRORS['genome_variant.end_int'] = end_msg % "end_int"
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)

def validate_alternate_bases(tile_var_seq, alternate_bases, through_start, through_end):
    """
        check the genome variant alternate bases are the bases in the variant
    """
    VALIDATION_ERRORS = {}
    if through_start < 0:
        VALIDATION_ERRORS['start'] = "start is less than 0"
    if through_start > len(tile_var_seq):
        VALIDATION_ERRORS['start'] = "start is larger than the length of the tile_variant_sequence"
    if through_end < 0:
        VALIDATION_ERRORS['end'] = "end is less than 0"
    if through_end > len(tile_var_seq):
        VALIDATION_ERRORS['end'] = "end is larger than the length of the tile_variant_sequence"
    if through_end < through_start:
        VALIDATION_ERRORS['start-end'] = "end is larger than start"
    if tile_var_seq[through_start:through_end].upper() != alternate_bases.strip('-').upper():
        VALIDATION_ERRORS['genome_variant.alternate_bases'] = "Alternate bases (%s) do not match bases in tile variant (%s)" % (alternate_bases, tile_var_seq[through_start:through_end])
    if len(VALIDATION_ERRORS) > 0:
        raise TileLibraryValidationError(VALIDATION_ERRORS)
