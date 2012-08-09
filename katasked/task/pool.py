import heapq
import multiprocessing
import operator
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
        self.running = []
        self.sequence_num = 0
        self.sequence_map = {}

    def add_task(self, task):
        """Add a task to the pool"""
        task.pool = self
        self.to_run.add(task)
        
    def apply_async(self, *args, **kwargs):
        return self.pool.apply_async(*args, **kwargs)

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

        to_return = []
        for runningtask in finished_running:
            res = runningtask.result.get()
            runningtask.task.finished(res)
            to_return.append(runningtask.task)

        if len(self.running) >= self.num_procs:
            return to_return

        num_to_run = min(self.num_procs - len(self.running), len(self.to_run))
        if num_to_run < 1:
            return to_return
        
        task_priorities = priority.calc_priority(pandastate, self.to_run)
        largestN = heapq.nlargest(num_to_run, task_priorities.iteritems(), key=operator.itemgetter(1))
        
        for task, _ in largestN:
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
    
    def __init__(self, num_procs):
        self.pools = {}
        for pool_type in self.POOL_TYPES:
            self.pools[pool_type] = TaskPool(num_procs, type_name="%s" % str(pool_type))
    
    def add_task(self, task):
        for pool_type in self.POOL_TYPES:
            if isinstance(task, pool_type):
                task.multiplexer = self
                self.pools[pool_type].add_task(task)
                return
        
        raise Exception("Unknown task type given to MultiplexPool")

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
