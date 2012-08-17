import math
import heapq
import json
import operator
import collections
import random

import panda3d.core as p3d

import katasked.task.base as taskbase

MAX_SOLID_ANGLE = 4.0 * math.pi

class PriorityAlgorithm(object):
    def combine(self, metrics):
        raise NotImplementedError()

class SingleSolidAngle(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.solid_angle

class SingleFuture2SolidAngle(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.future_2_solid_angle

class SingleFuture5SolidAngle(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.future_5_solid_angle

class SingleCameraAngle(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.camera_angle

class SingleFuture2CameraAngle(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.future_2_camera_angle

class SingleFuture5CameraAngle(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.future_5_camera_angle

class SinglePerceptualError(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.perceptual_error

class Random(PriorityAlgorithm):
    def combine(self, metrics):
        # note: not actually used because of optimization below using random.sample
        raise NotImplementedError()
        return random.random()

class HandTuned1(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.solid_angle * 2000 + \
                metrics.future_2_solid_angle * 4000 + \
                metrics.future_5_solid_angle * 4000 + \
                metrics.camera_angle * 0.5 + \
                metrics.future_2_camera_angle * 0.75 + \
                metrics.future_5_camera_angle * 0.75 + \
                metrics.perceptual_error * 1

class HandTuned2(PriorityAlgorithm):
    def combine(self, metrics):
        return metrics.solid_angle * \
                metrics.future_2_solid_angle * \
                metrics.future_5_solid_angle * \
                metrics.camera_angle * \
                metrics.future_2_camera_angle * \
                metrics.future_5_camera_angle * \
                metrics.perceptual_error

class FromFile(PriorityAlgorithm):
    def __init__(self, fbuf):
        self.w = json.load(fbuf)
        assert isinstance(self.w['solid_angle'], float)
        assert isinstance(self.w['future_2_solid_angle'], float)
        assert isinstance(self.w['future_5_solid_angle'], float)
        assert isinstance(self.w['camera_angle'], float)
        assert isinstance(self.w['future_2_camera_angle'], float)
        assert isinstance(self.w['future_5_camera_angle'], float)
        assert isinstance(self.w['perceptual_error'], float)
    
    def combine(self, metrics):
        return metrics.solid_angle * self.w['solid_angle'] + \
                metrics.future_2_solid_angle * self.w['future_2_solid_angle'] + \
                metrics.future_5_solid_angle * self.w['future_5_solid_angle'] + \
                metrics.camera_angle * self.w['camera_angle'] + \
                metrics.future_2_camera_angle * self.w['future_2_camera_angle'] + \
                metrics.future_5_camera_angle * self.w['future_5_camera_angle'] + \
                metrics.perceptual_error * self.w['perceptual_error']

PRIORITY_ALGORITHMS = [Random,
                       SingleSolidAngle, SingleCameraAngle, SinglePerceptualError,
                       SingleFuture2SolidAngle, SingleFuture2CameraAngle,
                       SingleFuture5SolidAngle, SingleFuture5CameraAngle,
                       FromFile,
                       HandTuned1, HandTuned2]

PRIORITY_ALGORITHM_NAMES = dict((a.__name__, a) for a in PRIORITY_ALGORITHMS)

SELECTED_ALGORITHM = HandTuned1()

def set_priority_algorithm(algorithm):
    global SELECTED_ALGORITHM
    SELECTED_ALGORITHM = algorithm

def get_priority_algorithm_names():
    return PRIORITY_ALGORITHM_NAMES.keys()

def get_algorithm_by_name(name):
    return PRIORITY_ALGORITHM_NAMES[name]

class Metrics(object):
    def __init__(self):
        self.solid_angle = 0
        self.future_2_solid_angle = 0
        self.future_5_solid_angle = 0
        self.camera_angle = 0
        self.future_2_camera_angle = 0
        self.future_5_camera_angle = 0
        self.perceptual_error = 0
    
    def combine(self):
        return SELECTED_ALGORITHM.combine(self)

def calc_solid_angle(camera_pos, np):
    to_center = camera_pos - np.getPos()
    to_center_len = to_center.length()
    np_radius = np.getScale()[0]
    
    if to_center_len <= np_radius:
        solid_angle = MAX_SOLID_ANGLE
    else:
        sin_alpha = np_radius / to_center_len
        cos_alpha = math.sqrt(1.0 - sin_alpha * sin_alpha)
        solid_angle = 2.0 * math.pi * (1.0 - cos_alpha)
    
    return solid_angle / MAX_SOLID_ANGLE

def calc_camera_angle(camera_np, camera_forward, np):
    camera_np.lookAt(np.getPos())
    copied_forward = camera_np.getQuat().getForward()
    copied_forward.normalize()
    angle_change = copied_forward.angleDeg(camera_forward)
    return 1.0 - (angle_change / 360.0)

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
    curtime = pandastate.globalClock.getFrameTime()
    pandastate.camera_smoother.computeSmoothPosition(curtime + 2)
    camera_pos_future_2 = pandastate.camera_smoother.getSmoothPos()
    pandastate.camera_smoother.computeSmoothPosition(curtime + 5)
    camera_pos_future_5 = pandastate.camera_smoother.getSmoothPos()
    
    # needed for camera angle
    copied_camera = p3d.NodePath("tempnode1")
    camera_quat = pandastate.camera.getQuat()
    copied_camera.setQuat(camera_quat)
    copied_camera.setPos(camera_pos)
    camera_forward = camera_quat.getForward()
    camera_forward.normalize()
    
    copied_camera_future_2 = p3d.NodePath("tempnode2")
    pandastate.camera_smoother.applySmoothPosHpr(copied_camera_future_2, copied_camera_future_2)
    camera_quat_future_2 = copied_camera_future_2.getQuat()
    camera_forward_future_2 = camera_quat_future_2.getForward()
    camera_forward_future_2.normalize()
    
    copied_camera_future_5 = p3d.NodePath("tempnode2")
    pandastate.camera_smoother.applySmoothPosHpr(copied_camera_future_5, copied_camera_future_5)
    camera_quat_future_5 = copied_camera_future_5.getQuat()
    camera_forward_future_5 = camera_quat_future_5.getForward()
    camera_forward_future_5.normalize()
    
    for np, metrics in np_metrics.iteritems():
        
        # calc solid angle
        metrics.solid_angle = calc_solid_angle(camera_pos, np)
        metrics.future_2_solid_angle = calc_solid_angle(camera_pos_future_2, np)
        metrics.future_5_solid_angle = calc_solid_angle(camera_pos_future_5, np)
        
        # calc angle between camera and object
        metrics.camera_angle = calc_camera_angle(copied_camera, camera_forward, np)
        metrics.future_2_camera_angle = calc_camera_angle(copied_camera_future_2, camera_forward_future_2, np)
        metrics.future_5_camera_angle = calc_camera_angle(copied_camera_future_5, camera_forward_future_5, np)
    
    # combine metrics together
    task_priorities = collections.defaultdict(float)
    for model, np in pandastate.nodepaths.iteritems():
        if model.slug not in task_modelslugs:
            continue
        
        task = task_modelslugs[model.slug]
        metrics = np_metrics[np]
        
        combined_priority = metrics.combine()
        task_priorities[task] += combined_priority
        
        if isinstance(task, taskbase.DownloadTask):
            task_priorities[task] /= float(task.download_size)
    
    return task_priorities

def get_highest_N(pandastate, tasks, N):
    # optimization - don't bother calculating priority if it's random
    if isinstance(SELECTED_ALGORITHM, Random):
        return random.sample(tasks, N)
    
    task_priorities = calc_priority(pandastate, tasks)
    largestN = heapq.nlargest(N, task_priorities.iteritems(), key=operator.itemgetter(1))
    return [i[0] for i in largestN]
