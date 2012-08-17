import os
import shove
import open3dhub

class Cache(object):
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = os.path.abspath(os.path.dirname(__file__))
        self.cache_dir = cache_dir

        self.metadata_cache_file = os.path.join(self.cache_dir, '.cache')
        self.metadata_shover = shove.Shove(store='file://' + self.metadata_cache_file, compress=True, sync=1)
        
        self.hashdata_cache_file = os.path.join(self.cache_dir, '.hash-cache')
        self.hashdata_shover = shove.Shove(store='file://' + self.hashdata_cache_file, compress=True, sync=1)
        
        self.bamdata_cache_file = os.path.join(self.cache_dir, '.bam-cache')
        if not os.path.isdir(self.bamdata_cache_file):
            os.mkdir(self.bamdata_cache_file)

    def _cache_wrap(self, shover, key, func, *args, **kwargs):
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
    
    def cache_metadata_wrap(self, key, func, *args, **kwargs):
        return self._cache_wrap(self.metadata_shover, key, func, *args, **kwargs)
    
    def cache_data_wrap(self, key, func, *args, **kwargs):
        return self._cache_wrap(self.hashdata_shover, key, func, *args, **kwargs)
    
    def cache_bam_wrap(self, key, meshdata, boundsInfo, subfiles, modelslug):
        cachefile = os.path.join(self.bamdata_cache_file, key)
        if not os.path.isfile(cachefile):
            open3dhub._load_into_bamfile(cachefile, meshdata, boundsInfo, subfiles, modelslug)
        return cachefile
    
    def is_bam_cached(self, key):
        cachefile = os.path.join(self.bamdata_cache_file, key)
        return os.path.isfile(cachefile)
    
    def add_bam(self, key, np):
        cachefile = os.path.join(self.bamdata_cache_file, key)
        np.writeBamFile(cachefile)
    
    def get_bam_file(self, key):
        return os.path.join(self.bamdata_cache_file, key)

_cache = None

def init_cache(cache_dir=None):
    global _cache
    _cache = Cache(cache_dir)

def cache_metadata_wrap(*args, **kwargs):
    if _cache is None:
        init_cache()
    return _cache.cache_metadata_wrap(*args, **kwargs)

def cache_data_wrap(*args, **kwargs):
    if _cache is None:
        init_cache()
    return _cache.cache_data_wrap(*args, **kwargs)

def cache_bam_wrap(*args, **kwargs):
    if _cache is None:
        init_cache()
    return _cache.cache_bam_wrap(*args, **kwargs)

def is_bam_cached(key):
    if _cache is None:
        init_cache()
    return _cache.is_bam_cached(key)

def add_bam(key, np):
    if _cache is None:
        init_cache()
    return _cache.add_bam(key, np)

def get_bam_file(key):
    if _cache is None:
        init_cache()
    return _cache.get_bam_file(key)
