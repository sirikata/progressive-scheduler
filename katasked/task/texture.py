import katasked.task.base as base
import katasked.open3dhub as open3dhub

def _run(atlas_hash, levelinfo, modelslug):
    with base.print_exc_onerror():
        texture_data = open3dhub.hashfetch(atlas_hash, httprange=(levelinfo['offset'], levelinfo['length']))
        return open3dhub.load_into_bamfile(None, None, texture_data, modelslug)

class TextureDownloadTask(base.DownloadTask):
    """Downloads a texture level"""
    
    def __init__(self, modelslug, metadata, levelinfo):
        super(TextureDownloadTask, self).__init__(modelslug)
        self.metadata = metadata
        self.levelinfo = levelinfo
        
        # gzip download size for textures is just the texture size itself
        # because they are encoded as JPEG, which gzip doesn't really do
        # anything for
        self.download_size = self.levelinfo['length']

    def run(self):
        progressive = self.metadata['metadata']['types']['progressive']
        atlas_hash = progressive['mipmaps']['./atlas.jpg']['hash']
        modelslug = self.modelslug + "_texture_%d" % self.levelinfo['offset']
        return self.pool.apply_async(_run, [atlas_hash, self.levelinfo, modelslug])

    def finished(self, result):
        self.bam_file = result
        
        # add next texture level if exists (> self)
        progressive = self.metadata['metadata']['types']['progressive']
        atlas_ranges = progressive['mipmaps']['./atlas.jpg']['byte_ranges']
        for levelinfo in atlas_ranges:
            if levelinfo['offset'] > self.levelinfo['offset']:
                t = TextureDownloadTask(self.modelslug, self.metadata, levelinfo)
                self.multiplexer.add_task(t)
                break

    def __str__(self):
        return '<TextureDownloadTask %s>' % self.modelslug
    def __repr__(self):
        return str(self)
