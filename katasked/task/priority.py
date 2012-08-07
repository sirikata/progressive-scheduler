import math
import collections

MAX_SOLID_ANGLE = 4.0 * math.pi

class Metrics(object):
    def __init__(self):
        self.solid_angle = 0

def calc_priority(pandastate, tasks):
    task_modelslugs = dict((t.modelslug, t) for t in tasks)
    
    np_metrics = {}
    for model, np in pandastate.nodepaths.iteritems():
        if model.slug in task_modelslugs:
            np_metrics[np] = Metrics()
    
    # calc solid angle
    camera_pos = pandastate.camera.getPos()
    for np, metrics in np_metrics.iteritems():
        to_center = camera_pos - np.getPos()
        to_center_len = to_center.length()
        np_radius = np.getScale()[0]
        
        if to_center_len <= np_radius:
            solid_angle = MAX_SOLID_ANGLE
        else:
            sin_alpha = np_radius / to_center_len
            cos_alpha = math.sqrt(1.0 - sin_alpha * sin_alpha)
            solid_angle = 2.0 * math.pi * (1.0 - cos_alpha)
        
        metrics.solid_angle = solid_angle / MAX_SOLID_ANGLE
    
    # combine metrics together
    task_priorities = collections.defaultdict(float)
    for model, np in pandastate.nodepaths.iteritems():
        if model.slug not in task_modelslugs:
            continue
        
        task = task_modelslugs[model.slug]
        metrics = np_metrics[np]
        
        combined_priority = metrics.solid_angle
        task_priorities[task] += combined_priority
    
    return task_priorities
