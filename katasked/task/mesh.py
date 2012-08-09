import katasked.task.base as base
import katasked.open3dhub as open3dhub
import katasked.task.texture as texturetask
import katasked.task.refinement as refinementtask
import katasked.scene as scene

def _run_download(mesh_hash, atlas_hash, base_level):
    with base.print_exc_onerror():
        mesh_data = open3dhub.hashfetch(mesh_hash)
        texture_data = open3dhub.hashfetch(atlas_hash, httprange=(base_level['offset'], base_level['length']))
        return (mesh_data, texture_data)

class MeshDownloadTask(base.DownloadTask):
    """Downloads the base mesh and texture of a progressive mesh"""
    
    def __init__(self, modelslug, metadata):
        super(MeshDownloadTask, self).__init__(modelslug)
        self.metadata = metadata
        
        self.progressive = self.metadata['metadata']['types']['progressive']
        self.download_size = self.progressive['size_gzip']
        
        self.perceptual_error = self.progressive['progressive_perceptual_error'][0]["pixel_error"]

    def run(self):
        progressive = self.metadata['metadata']['types']['progressive']
        mesh_hash = progressive['hash']
        atlas_ranges = progressive['mipmaps']['./atlas.jpg']['byte_ranges']
        atlas_hash = progressive['mipmaps']['./atlas.jpg']['hash']
        
        base_level = None
        for levelinfo in atlas_ranges:
            base_level = levelinfo
            if levelinfo['width'] >= 128 or levelinfo['height'] >= 128:
                break
        
        return self.pool.apply_async(_run_download, [mesh_hash, atlas_hash, base_level])

    def finished(self, result):
        t = MeshLoadTask(self.modelslug, self.metadata, *result)
        self.multiplexer.add_task(t)

    def __str__(self):
        return '<MeshDownloadTask %s>' % self.modelslug
    def __repr__(self):
        return str(self)

def _run_load(mesh_data, boundsInfo, texture_data, modelslug):
    with base.print_exc_onerror():
        return open3dhub.load_into_bamfile(mesh_data, boundsInfo, {'atlas.jpg': texture_data}, modelslug)

class MeshLoadTask(base.LoadTask):
    """Takes raw base mesh download data and turns it into a BAM ready to load on disk"""
    
    def __init__(self, modelslug, metadata, mesh_data, texture_data):
        super(MeshLoadTask, self).__init__(modelslug)
        self.metadata = metadata
        self.progressive = self.metadata['metadata']['types']['progressive']
        self.boundsInfo = scene.SceneModel.extract_bounds_info(self.metadata)
        self.mesh_data = mesh_data
        self.texture_data = texture_data
        
        self.perceptual_error = self.progressive['progressive_perceptual_error'][0]["pixel_error"]

    def run(self):
        return self.pool.apply_async(_run_load, [self.mesh_data, self.boundsInfo, self.texture_data, self.modelslug])

    def _update_loaded_already(self, loaded_already):
        # no need to update perceptual error here, texture and refinement tasks get loaded after this
        pass

    def finished(self, result):
        self.bam_file = result
        
        base_loaded = self.progressive['progressive_perceptual_error'][0]
        
        # add next texture level if exists (> 128x128)
        atlas_ranges = self.progressive['mipmaps']['./atlas.jpg']['byte_ranges']
        for levelinfo in atlas_ranges:
            if levelinfo['width'] > 128 or levelinfo['height'] > 128:
                t = texturetask.TextureDownloadTask(self.modelslug, self.metadata, levelinfo, base_loaded)
                self.multiplexer.add_task(t)
                break
            
        progressive_stream = self.progressive['progressive_stream']
        if progressive_stream is not None:
            t = refinementtask.MeshRefinementDownloadTask(self.modelslug, self.metadata, loaded_already=base_loaded)
            self.multiplexer.add_task(t)

    def __str__(self):
        return '<MeshLoadTask %s>' % self.modelslug
    def __repr__(self):
        return str(self)
