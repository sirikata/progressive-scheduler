import os
import shove
from meshtool.filters.print_filters.print_bounds import getBoundsInfo
import open3dhub

CURDIR = os.path.abspath(os.path.dirname(__file__))
CACHE = os.path.join(CURDIR, '.cache')
SHELF = shove.Shove(store='file://' + CACHE, compress=True, sync=1)

HASH_CACHE = os.path.join(CURDIR, '.hash-cache')
HASH_SHELF = shove.Shove(store='file://' + HASH_CACHE, compress=True, sync=1)

def get_tag(tag):
    tagkey = "TAG_" + str(tag)
    if tagkey not in SHELF:
        SHELF[tagkey] = open3dhub.get_search_list('tags:"%s"' % tag)
    return SHELF[tagkey]

def get_bounds(path):
    pathkey = 'BOUNDS_' + str(path)
    if pathkey not in SHELF:
        metadata, mesh = open3dhub.path_to_mesh(path, cache=True)
        SHELF[pathkey] = getBoundsInfo(mesh)
    
    return SHELF[pathkey]

def get_metadata(path):
    key = 'METADATA_' + str(path)
    if key not in SHELF:
        metadata, mesh = open3dhub.path_to_mesh(path, cache=True)
        SHELF[key] = metadata
    
    return SHELF[key]

def hashfetch(dlhash, httprange=None):
    key = 'HASH_' + str(dlhash)
    if key not in HASH_SHELF:
        data = open3dhub._hashfetch(dlhash, httprange)
        HASH_SHELF[key] = data
    
    return HASH_SHELF[key]
