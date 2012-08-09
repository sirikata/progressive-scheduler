import os
import shove
import open3dhub

CURDIR = os.path.abspath(os.path.dirname(__file__))
METADATA_CACHE_FILE = os.path.join(CURDIR, '.cache')
METADATA_SHOVER = shove.Shove(store='file://' + METADATA_CACHE_FILE, compress=True, sync=1)

HASHDATA_CACHE_FILE = os.path.join(CURDIR, '.hash-cache')
HASHDATA_SHOVER = shove.Shove(store='file://' + HASHDATA_CACHE_FILE, compress=True, sync=1)

BAMDATA_CACHE_FILE = os.path.join(CURDIR, '.bam-cache')
if not os.path.isdir(BAMDATA_CACHE_FILE):
    os.mkdir(BAMDATA_CACHE_FILE)

def _cache_wrap(shover, key, func, *args, **kwargs):
    def _getkey():
        if key not in shover:
            shover[key] = func(*args, **kwargs)
        return shover[key]
    
    # If the program crashes while writing a cache key to disk, it can result
    # in invalid data that can't be unpickled. It manifests as an EOFError in
    # the unpickler, so if this happens, just delete the key and try again.
    try:
        return _getkey()
    except EOFError:
        del shover[key]
        return _getkey()

def cache_metadata_wrap(key, func, *args, **kwargs):
    return _cache_wrap(METADATA_SHOVER, key, func, *args, **kwargs)

def cache_data_wrap(key, func, *args, **kwargs):
    return _cache_wrap(HASHDATA_SHOVER, key, func, *args, **kwargs)

def cache_bam_wrap(key, meshdata, boundsInfo, subfiles, modelslug):
    cachefile = os.path.join(BAMDATA_CACHE_FILE, key)
    if not os.path.isfile(cachefile):
        open3dhub._load_into_bamfile(cachefile, meshdata, boundsInfo, subfiles, modelslug)
    return cachefile
