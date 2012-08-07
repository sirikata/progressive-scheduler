import contextlib
import traceback

@contextlib.contextmanager
def print_exc_onerror():
    try:
        yield
    except:
        traceback.print_exc()
        raise

class Task(object):
    """Base class for tasks that need to be executed"""
    
    def __init__(self, modelslug):
        """Creates a task with given priority and list of dependent tasks"""
        self.modelslug = modelslug
        self.pool = None

    def run(self):
        """Should call apply_async on given pool to execute task"""
        raise NotImplementedError()
    
    def finished(self, result):
        """Called when the result of a task is complete, implemented by child classes"""
        raise NotImplementedError()

class DownloadTask(Task):
    """Base task class for downloading something"""
    pass

class LoadTask(Task):
    """Base task class for loading something"""
    pass
