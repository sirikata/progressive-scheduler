import heapq
import multiprocessing
import operator
import katasked.task.priority as priority
import katasked.task.result as result

class TaskPool(object):
    """A task pool for running tasks"""
    
    def __init__(self, num_procs):
        """Initializes the pool with given number of processes"""
        self.num_procs = num_procs
        self.pool = multiprocessing.Pool(self.num_procs)
        self.to_run = set()
        self.running = []

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
            print 'taskpool finished a task'
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
        print 'running', len(largestN), 'tasks'
        print largestN
        
        for task, _ in largestN:
            self.to_run.remove(task)
            self.running.append(result.TaskResult(task=task, result=task.run()))
        
        return to_return
