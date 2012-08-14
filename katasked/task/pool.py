import multiprocessing
import time
import collections
import katasked.task.priority as priority
import katasked.task.result as result
import katasked.task.base as taskbase

class TaskPool(object):
    """A task pool for running tasks"""
    
    def __init__(self, num_procs, type_name=""):
        """Initializes the pool with given number of processes"""
        self.num_procs = num_procs
        self.type_name = type_name
        self.pool = multiprocessing.Pool(self.num_procs)
        self.to_run = set()
        self.task_slug_map = collections.defaultdict(set)
        self.running = []
        self.sequence_num = 0
        self.sequence_map = {}
        self.last_action = time.time()

    def add_task(self, task):
        """Add a task to the pool"""
        task.pool = self
        self.task_slug_map[task.modelslug].add(task)
        self.to_run.add(task)
        
    def apply_async(self, *args, **kwargs):
        return self.pool.apply_async(*args, **kwargs)

    def get_tasks_by_slug(self, slug):
        return self.task_slug_map[slug]

    def _check_waiting(self):
        """Checks list of running tasks for any that have finished"""
        finished = []
        new_running = []
        for runningtask in self.running:
            if runningtask.result.ready():
                finished.append(runningtask)
            else:
                new_running.append(runningtask)
        self.running = new_running
        return finished

    def empty(self):
        """Returns True if the pool is empty"""
        return len(self.to_run) + len(self.running) == 0

    def poll(self, pandastate):
        """Executes tasks and gets results. Should be executed often."""
        finished_running = self._check_waiting()

        now = time.time()
        if now - self.last_action > 5:
            self.last_action = now
            print 'Waiting on', len(self.running), 'tasks to complete', len(self.to_run), 'queued.'
        
        to_return = []
        for runningtask in finished_running:
            self.task_slug_map[runningtask.task.modelslug].remove(runningtask.task)
        for runningtask in finished_running:
            res = runningtask.result.get()
            runningtask.task.finished(res)
            to_return.append(runningtask.task)

        if len(self.running) >= self.num_procs:
            return to_return

        num_to_run = min(self.num_procs - len(self.running), len(self.to_run))
        if num_to_run < 1:
            return to_return
        
        largestN = priority.get_highest_N(pandastate, self.to_run, num_to_run)
        
        self.last_action = now
        
        for task in largestN:
            self.sequence_map[task] = self.sequence_num
            print "==(%d)==>" % self.sequence_num, task
            self.sequence_num += 1
            
            self.to_run.remove(task)
            self.running.append(result.TaskResult(task=task, result=task.run()))
        
        for outtask in to_return:
            print "<==(%d)==" % self.sequence_map[outtask], outtask
            del self.sequence_map[outtask]
        
        return to_return

class MultiplexPool(object):
    """A task pool that multiplexes tasks across multiple TaskPool objects"""
    
    POOL_TYPES = [taskbase.DownloadTask, taskbase.LoadTask]
    NUM_PROCS = {taskbase.DownloadTask: 4,
                 taskbase.LoadTask: multiprocessing.cpu_count()}
    
    def __init__(self):
        self.pools = {}
        for pool_type in self.POOL_TYPES:
            self.pools[pool_type] = TaskPool(self.NUM_PROCS[pool_type], type_name="%s" % str(pool_type))
    
    def add_task(self, task):
        for pool_type in self.POOL_TYPES:
            if isinstance(task, pool_type):
                task.multiplexer = self
                self.pools[pool_type].add_task(task)
                return
        
        raise Exception("Unknown task type given to MultiplexPool")

    def get_tasks_by_slug(self, slug):
        tasks = []
        for pool in self.pools.itervalues():
            tasks.extend(pool.get_tasks_by_slug(slug))
        return tasks

    def empty(self):
        for pool in self.pools.itervalues():
            if not pool.empty():
                return False
        return True

    def poll(self, pandastate):
        finished = []
        for pool in self.pools.itervalues():
            finished.extend(pool.poll(pandastate))
        return finished
