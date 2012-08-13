import katasked.task.base as base
import katasked.scene as scene
import katasked.open3dhub as open3dhub
import katasked.task.mesh as meshtask

def _run(path):
    with base.print_exc_onerror():
        return open3dhub.get_metadata(path)

class MetadataDownloadTask(base.DownloadTask):
    """Downloads metadata about a model"""
    
    def __init__(self, modelslug):
        super(MetadataDownloadTask, self).__init__(modelslug)
        
        # metadata gzip download size varies from about 2KB-4KB
        # just use 5KB as a conservative estimate
        self.download_size = 1024 * 5
        
        # zero pixels, basically disabling for metadata
        self.perceptual_error = 0
    
    def run(self):
        path = scene.SceneModel.unslug(self.modelslug)
        return self.pool.apply_async(_run, [path])

    def finished(self, result):
        self.metadata = result
        t = meshtask.MeshDownloadTask(self.modelslug, result)
        self.multiplexer.add_task(t)

    def __str__(self):
        return '<MetadataDownloadTask %s>' % self.modelslug
    def __repr__(self):
        return str(self)
