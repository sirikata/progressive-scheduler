import katasked.task.base as base
import katasked.open3dhub as open3dhub
import meshtool.filters.print_filters.print_pm_perceptual_error as percepfilter
import meshtool.filters.panda_filters.pdae_utils as pdae_utils

def _run(progressive_stream_hash, offset, length, refinements_read, num_refinements, previous_data):
    with base.print_exc_onerror():
        pm_data = previous_data + open3dhub.hashfetch(progressive_stream_hash, httprange=(offset, length))
        (refinements_read, num_refinements, pm_refinements, data_left) = pdae_utils.readPDAEPartial(pm_data, refinements_read, num_refinements)
        return (refinements_read, num_refinements, pm_refinements, data_left)

class MeshRefinementDownloadTask(base.DownloadTask):
    """Downloads a mesh refinement chunk"""
    
    def __init__(self, modelslug, metadata, offset=0, refinements_read=0, num_refinements=None, previous_data=""):
        super(MeshRefinementDownloadTask, self).__init__(modelslug)
        self.metadata = metadata
        self.offset = offset
        self.refinements_read = refinements_read
        self.num_refinements = num_refinements
        self.previous_data = previous_data
        
        self.progressive = self.metadata['metadata']['types']['progressive']
        self.progressive_stream_hash = self.progressive['progressive_stream']
        self.progressive_stream_size = self.progressive['progressive_stream_size']
        self.length = min(self.progressive_stream_size - self.offset, percepfilter.PM_CHUNK_SIZE)
        
        progressive_stream_size_gzip = self.progressive['progressive_stream_size_gzip']
        self.percentage = float(self.length) / self.progressive_stream_size
        
        # This is only an estimate, since the gzip size of a range request is not
        # going to be exactly the same as the gzip size of the whole file multiplied
        # by the ratio of the size of the range to the size of the whole file.
        # However, the estimate is going to be pretty close, so it suffices.
        self.download_size = self.percentage * progressive_stream_size_gzip 

    def run(self):
        return self.pool.apply_async(_run, [self.progressive_stream_hash,
                                            self.offset,
                                            self.length,
                                            self.refinements_read,
                                            self.num_refinements,
                                            self.previous_data])

    def finished(self, result):
        refinements_read, num_refinements, pm_refinements, data_left = result
        self.pm_refinements = pm_refinements

        newoffset = self.offset + self.length
        if newoffset < self.progressive_stream_size:
            t = MeshRefinementDownloadTask(self.modelslug,
                                           self.metadata,
                                           newoffset,
                                           refinements_read,
                                           num_refinements,
                                           data_left)
            self.multiplexer.add_task(t)

    def __str__(self):
        return '<MeshRefinementDownloadTask %s>' % self.modelslug
    def __repr__(self):
        return str(self)
