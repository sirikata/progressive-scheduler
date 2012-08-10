import math
import collections

import panda3d.core as p3d

import katasked.task.base as taskbase

MAX_SOLID_ANGLE = 4.0 * math.pi

class Metrics(object):
    def __init__(self):
        self.solid_angle = 0
        self.camera_angle = 0
        self.perceptual_error = 0
    
    def combined(self):
        # completely arbitrary weights
        return self.solid_angle * 10000 + \
                self.camera_angle * 1 + \
                self.perceptual_error * 1

def calc_priority(pandastate, tasks):
    task_modelslugs = dict((t.modelslug, t) for t in tasks)
    
    np_metrics = {}
    for model, np in pandastate.nodepaths.iteritems():
        if model.slug in task_modelslugs:
            np_metrics[np] = Metrics()
            
            # add perceptual error, same for all models for a given task
            perceptual_error = task_modelslugs[model.slug].perceptual_error
            perceptual_error = 1.0 - (float(perceptual_error) / (1024 * 768))
            np_metrics[np].perceptual_error = perceptual_error
    
    # needed for solid angle
    camera_pos = pandastate.camera.getPos()
    
    # needed for camera angle
    copied_np = p3d.NodePath("tempnode")
    camera_quat = pandastate.camera.getQuat()
    copied_np.setQuat(camera_quat)
    copied_np.setPos(camera_pos)
    camera_forward = camera_quat.getForward()
    camera_forward.normalize()
    
    for np, metrics in np_metrics.iteritems():
        
        # calc solid angle
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
        
        
        # calc angle between camera and object
        copied_np.lookAt(np.getPos())
        copied_forward = copied_np.getQuat().getForward()
        copied_forward.normalize()
        angle_change = copied_forward.angleDeg(camera_forward)
        metrics.camera_angle = 1.0 - (angle_change / 360.0)
    
    # combine metrics together
    task_priorities = collections.defaultdict(float)
    for model, np in pandastate.nodepaths.iteritems():
        if model.slug not in task_modelslugs:
            continue
        
        task = task_modelslugs[model.slug]
        metrics = np_metrics[np]
        
        combined_priority = metrics.combined()
        task_priorities[task] += combined_priority
        
        if isinstance(task, taskbase.DownloadTask):
            task_priorities[task] /= float(task.download_size)
    
    return task_priorities
