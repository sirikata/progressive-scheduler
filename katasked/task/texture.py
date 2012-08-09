import katasked.task.base as base
import katasked.open3dhub as open3dhub

def _run(atlas_hash, levelinfo, modelslug):
    with base.print_exc_onerror():
        texture_data = open3dhub.hashfetch(atlas_hash, httprange=(levelinfo['offset'], levelinfo['length']))
        return open3dhub.load_into_bamfile(None, None, texture_data, modelslug)

class TextureDownloadTask(base.DownloadTask):
    """Downloads a texture level"""
    
    def __init__(self, modelslug, metadata, levelinfo, loaded_already):
        super(TextureDownloadTask, self).__init__(modelslug)
        self.metadata = metadata
        self.levelinfo = levelinfo
        self.loaded_already = loaded_already
        self.progressive = self.metadata['metadata']['types']['progressive']
        self.perceptual_error = self._calc_perceptual_error()
        
        # gzip download size for textures is just the texture size itself
        # because they are encoded as JPEG, which gzip doesn't really do
        # anything for
        self.download_size = self.levelinfo['length']

    def _update_loaded_already(self, loaded_already):
        self.loaded_already = loaded_already
        self.perceptual_error = self._calc_perceptual_error()

    def _calc_current_loaded(self):
        error_data = self.progressive['progressive_perceptual_error']
        cur_triangles = self.loaded_already['triangles']
        
        for error_level in error_data:
            if error_level['width'] == self.levelinfo['width'] and \
               error_level['height'] == self.levelinfo['height'] and \
               error_level['triangles'] == cur_triangles:
                
                return error_level
            
        raise Exception("Couldn't find current error data")

    def _calc_perceptual_error(self):
        return self._calc_current_loaded()['pixel_error']

    def run(self):
        atlas_hash = self.progressive['mipmaps']['./atlas.jpg']['hash']
        modelslug = self.modelslug + "_texture_%d" % self.levelinfo['offset']
        return self.pool.apply_async(_run, [atlas_hash, self.levelinfo, modelslug])

    def finished(self, result):
        self.bam_file = result
        
        # add next texture level if exists (> self)
        progressive = self.metadata['metadata']['types']['progressive']
        atlas_ranges = progressive['mipmaps']['./atlas.jpg']['byte_ranges']
        for levelinfo in atlas_ranges:
            if levelinfo['offset'] > self.levelinfo['offset']:
                t = TextureDownloadTask(self.modelslug, self.metadata, levelinfo, self.loaded_already)
                self.multiplexer.add_task(t)
                break
        
        next_already_loaded = self._calc_current_loaded()
        for t in self.multiplexer.get_tasks_by_slug(self.modelslug):
            t._update_loaded_already(next_already_loaded)

    def __str__(self):
        return '<TextureDownloadTask %s>' % self.modelslug
    def __repr__(self):
        return str(self)
