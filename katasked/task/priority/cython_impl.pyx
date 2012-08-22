from libcpp cimport bool

cdef extern from "math.h":
    double sqrt(double x)

cdef extern from "<string>" namespace "std":
    cdef cppclass string:
        string()
        string(char *)
        char* c_str()
        bint operator==(string&)
        bint operator==(char*)

cdef char* CONST_tempnode = "tempnode"

cdef extern from "py_panda.h":
    cdef struct Dtool_PyInstDef:
        void* _ptr_to_object

cdef void* get_ptr(object o):
    return (<Dtool_PyInstDef*>o)._ptr_to_object

cdef extern from "nodePath.h":
    cdef cppclass NodePath:
        NodePath()
        NodePath(string)
        
        LPoint3f get_pos()
        void set_pos(LPoint3f)
        
        LVecBase3 get_scale()
        
        LQuaternionf get_quat()
        void set_quat(LQuaternionf)
        
        NodePath attach_new_node(string)
        
        void look_at(LPoint3f point)

cdef extern from "lvecBase3.h":
    cdef cppclass LVecBase3:
        bool normalize()
        float length()
        float get_x()

cdef extern from "lpoint3.h":
    cdef cppclass LPoint3f(LVecBase3):
        LPoint3f operator+(LPoint3f)
        LPoint3f operator-(LPoint3f)
        LPoint3f operator*(float)

cdef extern from "lvector3.h":
    cdef cppclass LVector3f(LVecBase3):
        float angle_deg(LVector3f other)

cdef extern from "lquaternion.h":
    cdef cppclass LQuaternionf:
        LVector3f get_forward()

cdef extern from "smoothMover.h":
    cdef cppclass SmoothMover:
        bool compute_smooth_position(double)
        void apply_smooth_pos_hpr(NodePath, NodePath)
        LPoint3f get_smooth_pos()

cdef extern from "boundingSphere.h":
    cdef cppclass BoundingSphere:
        LPoint3f get_center()
        float get_radius()
        int contains(LPoint3f point)

import math
import heapq
import json
import operator
import collections
import random

import panda3d.core as p3d

import katasked.task.base as taskbase

cdef float PI = 3.14159265359
cdef float MAX_SOLID_ANGLE = 4.0 * PI

cdef class PriorityAlgorithm:
    cpdef combine(self, Metrics metrics):
        raise NotImplementedError()

cdef class SingleSolidAngle(PriorityAlgorithm):
    name = 'Solid Angle'
    
    cpdef combine(self, Metrics metrics):
        return metrics.solid_angle

cdef class SingleFuture2SolidAngle(PriorityAlgorithm):
    name = 'Solid Angle +2'
    
    cpdef combine(self, Metrics metrics):
        return metrics.future_2_solid_angle

cdef class SingleFuture5SolidAngle(PriorityAlgorithm):
    name = 'Solid Angle +5'
    
    cpdef combine(self, Metrics metrics):
        return metrics.future_5_solid_angle

cdef class SingleCameraAngle(PriorityAlgorithm):
    name = 'Camera Angle'
    
    cpdef combine(self, Metrics metrics):
        return metrics.camera_angle

cdef class SingleFuture2CameraAngle(PriorityAlgorithm):
    name = 'Camera Angle +2'
    
    cpdef combine(self, Metrics metrics):
        return metrics.future_2_camera_angle

cdef class SingleFuture5CameraAngle(PriorityAlgorithm):
    name = 'Camera Angle +5'
    
    cpdef combine(self, Metrics metrics):
        return metrics.future_5_camera_angle

cdef class SinglePerceptualError(PriorityAlgorithm):
    name = 'Perceptual Error'
    
    cpdef combine(self, Metrics metrics):
        return metrics.perceptual_error

cdef class Random(PriorityAlgorithm):
    name = 'Random'
    
    cpdef combine(self, Metrics metrics):
        # note: not actually used because of optimization below using random.sample
        raise NotImplementedError()

cdef class HandTuned1(PriorityAlgorithm):
    name = 'Hand Tuned Linear'
    
    cpdef combine(self, Metrics metrics):
        return metrics.solid_angle * 2000 + \
                metrics.future_2_solid_angle * 4000 + \
                metrics.future_5_solid_angle * 4000 + \
                metrics.camera_angle * 0.5 + \
                metrics.future_2_camera_angle * 0.75 + \
                metrics.future_5_camera_angle * 0.75 + \
                metrics.perceptual_error * 1

cdef class HandTuned2(PriorityAlgorithm):
    name = 'Hand Tuned Multiply'
    
    cpdef combine(self, Metrics metrics):
        return metrics.solid_angle * \
                metrics.future_2_solid_angle * \
                metrics.future_5_solid_angle * \
                metrics.camera_angle * \
                metrics.future_2_camera_angle * \
                metrics.future_5_camera_angle * \
                metrics.perceptual_error

cdef class FromFile(PriorityAlgorithm):
    def __init__(self, fbuf):
        self.w = json.load(fbuf)
        assert isinstance(self.w['solid_angle'], float)
        assert isinstance(self.w['future_2_solid_angle'], float)
        assert isinstance(self.w['future_5_solid_angle'], float)
        assert isinstance(self.w['camera_angle'], float)
        assert isinstance(self.w['future_2_camera_angle'], float)
        assert isinstance(self.w['future_5_camera_angle'], float)
        assert isinstance(self.w['perceptual_error'], float)
    
    cpdef combine(self, Metrics metrics):
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

cdef class Metrics:
    cdef public double solid_angle
    cdef public future_2_solid_angle
    cdef public future_5_solid_angle
    cdef public camera_angle
    cdef public future_2_camera_angle
    cdef public future_5_camera_angle
    cdef public perceptual_error
    
    def __init__(self):
        self.solid_angle = 0
        self.future_2_solid_angle = 0
        self.future_5_solid_angle = 0
        self.camera_angle = 0
        self.future_2_camera_angle = 0
        self.future_5_camera_angle = 0
        self.perceptual_error = 0
    
    cpdef double combine(self) except *:
        return SELECTED_ALGORITHM.combine(self)

cdef calc_solid_angle(LPoint3f camera_pos, NodePath* np):
    cdef LPoint3f to_center = camera_pos - np.get_pos()
    cdef float to_center_len = to_center.length()
    cdef float np_radius = np.get_scale().get_x()
    
    cdef float solid_angle
    cdef float sin_alpha
    cdef float cos_alpha
    
    if to_center_len <= np_radius:
        solid_angle = MAX_SOLID_ANGLE
    else:
        sin_alpha = np_radius / to_center_len
        cos_alpha = sqrt(1.0 - sin_alpha * sin_alpha)
        solid_angle = 2.0 * PI * (1.0 - cos_alpha)
    
    return solid_angle / MAX_SOLID_ANGLE

cdef calc_camera_angle(NodePath camera_np, LVector3f camera_forward, NodePath* np, BoundingSphere* obj_bounds):
    cdef int inside = obj_bounds.contains(camera_np.get_pos())
    if inside & 4:
        return 1.0
    
    cdef LPoint3f to_center = camera_np.get_pos() - obj_bounds.get_center()
    to_center.normalize()
    cdef LPoint3f closest_point = obj_bounds.get_center() + to_center * obj_bounds.get_radius()
    
    camera_np.look_at(closest_point)
    copied_forward = camera_np.get_quat().get_forward()
    copied_forward.normalize()
    angle_change = copied_forward.angle_deg(camera_forward)
    return 1.0 - (angle_change / 180.0)

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
    cdef NodePath* camera_np = <NodePath*>get_ptr(pandastate.camera)
    cdef LPoint3f camera_pos = camera_np.get_pos()
    cdef double curtime = pandastate.globalClock.getFrameTime()
    
    cdef SmoothMover* camera_smoother = <SmoothMover*>get_ptr(pandastate.camera_smoother)
    camera_smoother.compute_smooth_position(curtime + 2)
    cdef LPoint3f camera_pos_future_2 = camera_smoother.get_smooth_pos()
    camera_smoother.compute_smooth_position(curtime + 5)
    cdef LPoint3f camera_pos_future_5 = camera_smoother.get_smooth_pos()
    
    # needed for camera angle
    cdef NodePath copied_camera
    copied_camera = copied_camera.attach_new_node(string(CONST_tempnode))
    cdef LQuaternionf camera_quat = camera_np.get_quat()
    copied_camera.set_quat(camera_quat)
    copied_camera.set_pos(camera_pos)
    cdef LVector3f camera_forward = camera_quat.get_forward()
    camera_forward.normalize()
    
    cdef NodePath copied_camera_future_2
    copied_camera_future_2 = copied_camera_future_2.attach_new_node(string(CONST_tempnode))
    camera_smoother.apply_smooth_pos_hpr(copied_camera_future_2, copied_camera_future_2)
    cdef LQuaternionf camera_quat_future_2 = copied_camera_future_2.get_quat()
    cdef LVector3f camera_forward_future_2 = camera_quat_future_2.get_forward()
    camera_forward_future_2.normalize()
    
    cdef NodePath copied_camera_future_5
    copied_camera_future_5 = copied_camera_future_5.attach_new_node(string(CONST_tempnode))
    camera_smoother.apply_smooth_pos_hpr(copied_camera_future_5, copied_camera_future_5)
    cdef LQuaternionf camera_quat_future_5 = copied_camera_future_5.get_quat()
    cdef LVector3f camera_forward_future_5 = camera_quat_future_5.get_forward()
    camera_forward_future_5.normalize()
    
    cdef NodePath* npptr
    cdef BoundingSphere* obj_bounds
    for np, metrics in np_metrics.iteritems():
        
        # calc solid angle
        npptr = <NodePath*>get_ptr(np)
        metrics.solid_angle = calc_solid_angle(camera_pos, npptr)
        metrics.future_2_solid_angle = calc_solid_angle(camera_pos_future_2, npptr)
        metrics.future_5_solid_angle = calc_solid_angle(camera_pos_future_5, npptr)
        
        # calc angle between camera and object
        obj_bounds = <BoundingSphere*>get_ptr(pandastate.obj_bounds[np])
        metrics.camera_angle = calc_camera_angle(copied_camera, camera_forward, npptr, obj_bounds)
        metrics.future_2_camera_angle = calc_camera_angle(copied_camera_future_2, camera_forward_future_2, npptr, obj_bounds)
        metrics.future_5_camera_angle = calc_camera_angle(copied_camera_future_5, camera_forward_future_5, npptr, obj_bounds)
    
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