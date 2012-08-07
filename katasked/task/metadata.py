import katasked.task.base as base
import katasked.scene as scene
import katasked.open3dhub as open3dhub
import katasked.task.mesh as meshtask

def _run(path):
    with base.print_exc_onerror():
        return open3dhub.get_metadata(path)

class MetadataDownloadTask(base.DownloadTask):
    """Downloads metadata about a model"""
    def run(self):
        path = scene.SceneModel.unslug(self.modelslug)
        return self.pool.apply_async(_run, [path])

    def finished(self, result):
        t = meshtask.MeshDownloadTask(self.modelslug, result)
        self.pool.add_task(t)

    def __str__(self):
        return '<MetadataDownloadTask %s>' % self.modelslug
    def __repr__(self):
        return str(self)
