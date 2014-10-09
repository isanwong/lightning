#Testing performance

import time

from tile_library.models import Tile, TileVariant, TileLocusAnnotation, VarAnnotation
from tile_library import views
from django.db.models import Avg, Count, Max

chrom = 2
path = 21
min_pos, min_tile = views.convert_chromosome_to_tilename(chrom)
max_pos, max_tile = views.convert_chromosome_to_tilename(chrom+1)
max_pos -= 1
max_tile -= 1
min_path_pos, min_path_tile = views.convert_path_to_tilename(path)
max_path_pos, max_path_tile = views.convert_path_to_tilename(path+1)
max_path_pos -= 1
max_path_tile -= 1

def timeit(fn):
    n = time.time()
    x = fn()
    l = time.time()
    return l-n, x
def timeitarg(fn, arg):
    n = time.time()
    x = fn(arg)
    l = time.time()
    return l-n, x
print "Entire Genome:"
print "\tTile count()", timeit(Tile.objects.count)
print "\tTileVar count()", timeit(TileVariant.objects.count)
print "\tTileVar avglen", timeitarg(TileVariant.objects.aggregate, Avg('length'))
print "\tTileVar maxvar", timeitarg(TileVariant.objects.aggregate, Max('variant_value'))
print ""
print "Biggest Chromosome:"
print "\tTile count()", timeit(Tile.objects.filter(tilename__range=(min_pos, max_pos)).count)
print "\tTileVar count()", timeit(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).count)
print "\tTileVar avglen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Avg('length'))
print "\tTileVar maxvar", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_tile, max_tile)).aggregate, Max('variant_value'))
print ""
print "Biggest Path:"
print "\tTile count()", timeit(Tile.objects.filter(tilename__range=(min_path_pos, max_path_pos)).count)
print "\tTileVar count()", timeit(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).count)
print "\tTileVar avglen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Avg('length'))
print "\tTileVar avglen", timeitarg(TileVariant.objects.filter(tile_variant_name__range=(min_path_tile, max_path_tile)).aggregate, Max('variant_value'))
