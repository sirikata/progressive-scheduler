#!/usr/bin/env python2

import os
import sys
import json
import collections
import math
import time

import panda3d.core as p3d
from pandac.PandaModules import SmoothMover
import direct.showbase.ShowBase as ShowBase
import direct.interval.MopathInterval as MopathInterval
import direct.gui as gui
import meshtool.filters.panda_filters.pandacore as pcore
import meshtool.filters.panda_filters.pandacontrols as controls
import meshtool.filters.print_filters.print_pm_perceptual_error as percepfilter

import katasked.scene as scene
import katasked.motioncap as motioncap
import katasked.panda
import katasked.task.pool as pool
import katasked.task.metadata as metadata
import katasked.task.mesh as meshtask
import katasked.task.texture as texturetask
import katasked.task.refinement as refinementtask
import katasked.pdae_updater as pdae_updater

class LOAD_TYPE:
    INITIAL_MODEL = 0
    TEXTURE_UPDATE = 1
    MESH_REFINEMENT = 2

class ProgressiveLoader(ShowBase.ShowBase):
    
    def __init__(self, scenefile, capturefile=None, showstats=False, screenshot_dir=None):
        
        self.scenefile = scenefile
        self.capturefile = capturefile
        self.scene = scene.Scene.fromfile(scenefile)
        self.unique_models = set(m.slug for m in self.scene)
        self.multiplexer = pool.MultiplexPool()
        self.screenshot_dir = screenshot_dir
        
        print '%d objects in scene, %d unique' % (len(self.scene), len(self.unique_models))
        
        # turns on lazy loading of textures
        p3d.loadPrcFileData('', 'preload-textures 0')
        p3d.loadPrcFileData('', 'preload-simple-textures 1')
        p3d.loadPrcFileData('', 'compressed-textures 1')
        p3d.loadPrcFileData('', 'allow-incomplete-render 1')
        
        
        # window size to 1024x768
        p3d.loadPrcFileData('', 'win-size 1024 768')
        
        ShowBase.ShowBase.__init__(self)
        
        # background color sky blue
        self.win.setClearColorActive(True)
        self.win.setClearColor(p3d.VBase4(0.5294, 0.8078, 0.9215, 0))
        
        # create a nodepath for each unique model
        self.unique_nodepaths = dict((m, p3d.NodePath(m)) for m in self.unique_models)
        
        self.rigid_body_combiners = {}
        self.rigid_body_combiner_np = {}
        for m in self.unique_models:
            rbc = p3d.RigidBodyCombiner(m)
            self.rigid_body_combiners[m] = rbc
            np = p3d.NodePath(rbc)
            np.reparentTo(self.render)
            self.rigid_body_combiner_np[m] = np
        
        # find out how many objects are going to be instanced for each node
        self.instance_count = collections.defaultdict(int)
        for model in self.scene:
            self.instance_count[model.slug] += 1
        
        # then instance each unique model to its instantiation in the actual scene
        self.nodepaths = {}
        self.obj_bounds = {}
        self.nodepaths_byslug = collections.defaultdict(list)
        for model in self.scene:
            unique_np = self.unique_nodepaths[model.slug]
            node_name = model.slug + "_%.7g_%.7g_%.7g" % (model.x, model.y, model.z)
            
            if self.instance_count[model.slug] == 1:
                unique_np.setName(node_name)
                unique_np.reparentTo(self.render)
                np = unique_np
            else:
                np = self.rigid_body_combiner_np[model.slug].attachNewNode(node_name)
            
            self.nodepaths[model] = np
            self.nodepaths_byslug[model.slug].append(np)
            np.setPos(model.x, model.y, model.z)
            np.setScale(model.scale, model.scale, model.scale)
            q = p3d.Quat()
            q.setI(model.orient_x)
            q.setJ(model.orient_y)
            q.setK(model.orient_z)
            q.setR(model.orient_w)
            np.setQuat(q)
            self.obj_bounds[np] = p3d.BoundingSphere(np.getPos(), np.getScale()[0])
        
        for rbc in self.rigid_body_combiners.itervalues():
            rbc.collect()
        
        self.waiting = []
        self.pm_waiting = collections.defaultdict(list)
        self.models_loaded = set()
        self.loading_priority = 2147483647
        
        for m in self.unique_models:
            t = metadata.MetadataDownloadTask(m)
            self.multiplexer.add_task(t)
        
        self.disableMouse()
        pcore.attachLights(self.render)
        self.render.setShaderAuto()
        self.render.setTransparency(p3d.TransparencyAttrib.MNone)
        
        self.camLens.setFar(sys.maxint)
        self.camLens.setNear(8.0)
        self.render.setAntialias(p3d.AntialiasAttrib.MAuto)
        
        self.showstats = showstats
        if showstats:
            self.num_metadata_loaded = 0
            self.num_models_loaded = 0
            self.num_texture_updates = 0
            self.num_mesh_refinements = 0
            self.total_texture_updates = 0
            self.total_mesh_refinements = 0
            
            self.txtMetadataLoaded = gui.OnscreenText.OnscreenText(text='', style=1, pos=(0.01, -0.05),
                                                                 parent=self.a2dTopLeft, align=p3d.TextNode.ALeft,
                                                                 scale=0.05, fg=(0.1, 0.1, 0.1, 1), shadow=(0.9, 0.9, 0.9, 1))
            self.txtUniqueLoaded = gui.OnscreenText.OnscreenText(text='', style=1, pos=(0.01, -0.11),
                                                                 parent=self.a2dTopLeft, align=p3d.TextNode.ALeft,
                                                                 scale=0.05, fg=(0.1, 0.1, 0.1, 1), shadow=(0.9, 0.9, 0.9, 1))
            self.txtTextureUpdates = gui.OnscreenText.OnscreenText(text='', style=1, pos=(0.01, -0.17),
                                                                 parent=self.a2dTopLeft, align=p3d.TextNode.ALeft,
                                                                 scale=0.05, fg=(0.1, 0.1, 0.1, 1), shadow=(0.9, 0.9, 0.9, 1))
            self.txtMeshRefinements = gui.OnscreenText.OnscreenText(text='', style=1, pos=(0.01, -0.23),
                                                                 parent=self.a2dTopLeft, align=p3d.TextNode.ALeft,
                                                                 scale=0.05, fg=(0.1, 0.1, 0.1, 1), shadow=(0.9, 0.9, 0.9, 1))
            
            self.update_stats()
        
        self.globalClock = p3d.ClockObject.getGlobalClock()
        
        self.smooth_mover = SmoothMover()
        self.smooth_mover.setPredictionMode(SmoothMover.PMOn)
        self.smooth_mover.setSmoothMode(SmoothMover.SMOn)
        self.smooth_mover.setMaxPositionAge(10.0)
        self.smooth_mover.setAcceptClockSkew(False)
        self.smooth_mover.setDelay(0)
        
        self.pandastate = katasked.panda.PandaState(self.cam,
                                                    self.unique_nodepaths,
                                                    self.nodepaths,
                                                    self.smooth_mover,
                                                    self.globalClock,
                                                    self.obj_bounds)
        
        if self.capturefile is not None:
            self.capturedata = json.load(self.capturefile)
            self.duration = self.capturedata['duration']
            self.positions = self.capturedata['positions']
            self.rotations = self.capturedata['rotations']
            
            self.curve_creator = motioncap.CreateNurbsCurve()
            for pos, rot in zip(self.positions, self.rotations):
                self.curve_creator.addPoint(pos, rot)
            self.mopath = self.curve_creator.getMotionPath()
            
            self.interval = MopathInterval.MopathInterval(self.mopath, self.cam, duration=self.duration, name="Camera Replay")
        else:
            controls.KeyboardMovement()
            controls.MouseCamera()
        
        self.update_camera_predictor_task = self.taskMgr.doMethodLater(0.1, self.update_camera_predictor, 'update_camera_predictor')
        self.update_priority_task = self.taskMgr.doMethodLater(0.5, self.check_pool, 'check_pool')
        self.load_waiting_task = self.taskMgr.doMethodLater(0.1, self.load_waiting, 'load_waiting')
        
    def run(self):
        if self.screenshot_dir is not None:
            self.start_time = None
            self.screenshot_info = []
            self.screenshot_task = self.taskMgr.doMethodLater(0, self.trigger_screenshot, 'screenshot_task', sort=-1)
        
        if self.capturefile is not None:
            self.interval.start()
            self.taskMgr.doMethodLater(self.duration + 2.0, self.finished, 'exiter')
        
        ShowBase.ShowBase.run(self)
    
    def update_camera_predictor(self, task):
        curtime = self.globalClock.getFrameTime()
        self.smooth_mover.setPos(self.cam.getPos())
        self.smooth_mover.setHpr(self.cam.getHpr())
        self.smooth_mover.setTimestamp(curtime)
        self.smooth_mover.markPosition()
        
        return task.again
    
    def check_pool(self, task):
        t0 = time.time()
        finished_tasks = self.multiplexer.poll(self.pandastate)
        t1 = time.time()
        time_took = t1-t0
        print 'took', time_took * 1000
        time_wait = time_took * 2.0
        time_wait = min(time_wait, 1)
        time_wait = max(time_wait, 0.1)
        task.delayTime = time_wait
        
        if len(finished_tasks) == 0 and self.multiplexer.empty():
            print
            print 'FINISHED LOADING'
            print
            return task.done
        
        for t in finished_tasks:
            if isinstance(t, meshtask.MeshLoadTask):
                self.loader.loadModel(t.bam_file, callback=self.model_loaded, extraArgs=[t.modelslug], priority=self.loading_priority)
            elif isinstance(t, texturetask.TextureDownloadTask):
                self.loader.loadModel(t.bam_file, callback=self.texture_loaded, extraArgs=[t.modelslug], priority=self.loading_priority)
            elif isinstance(t, refinementtask.MeshRefinementDownloadTask):
                if t.modelslug in self.models_loaded:
                    self.waiting.append((LOAD_TYPE.MESH_REFINEMENT, t.modelslug, t.pm_refinements))
                else:
                    self.pm_waiting[t.modelslug].append(t.pm_refinements)
            elif isinstance(t, metadata.MetadataDownloadTask):
                if self.showstats:
                    self.num_metadata_loaded += 1
                    
                    progressive = t.metadata['metadata']['types']['progressive']
                    byte_ranges = progressive['mipmaps']['./atlas.jpg']['byte_ranges']
                    baselevel = len(byte_ranges)
                    for i, levelinfo in enumerate(byte_ranges):
                        if levelinfo['width'] >= 128 or levelinfo['height'] >= 128:
                            baselevel = i
                            break
                    self.total_texture_updates += len(byte_ranges[baselevel+1:])
                    
                    if 'progressive_stream_size' in progressive:
                        self.total_mesh_refinements += int(math.ceil(progressive['progressive_stream_size'] / float(percepfilter.PM_CHUNK_SIZE)))
                    
                    self.update_stats()
                
            self.loading_priority -= 1
        
        
        return task.again

    def model_loaded(self, modelpath, modelslug):
        self.models_loaded.add(modelslug)
        self.waiting.append((LOAD_TYPE.INITIAL_MODEL, modelpath, modelslug))
        for pm_refinements in self.pm_waiting[modelslug]:
            self.waiting.append((LOAD_TYPE.MESH_REFINEMENT, modelslug, pm_refinements))
        del self.pm_waiting[modelslug]
    
    def texture_loaded(self, modelpath, modelslug):
        newtex = modelpath.getChild(0).getTexture()
        np = self.unique_nodepaths[modelslug]
        self.waiting.append((LOAD_TYPE.TEXTURE_UPDATE, np, newtex))
        
    def load_waiting(self, task):
        task.delayTime = 0.2
        
        if len(self.waiting) > 0:
            args = self.waiting.pop(0)
            if args[0] == LOAD_TYPE.INITIAL_MODEL:
                modelpath, modelslug = args[1], args[2]
                
                np = self.unique_nodepaths[modelslug]
                modelnode = modelpath.getChild(0)
                geomnode = modelnode.getChild(0)
                trans = modelnode.getTransform()
                geomnode.setTransform(trans)
                self.unique_nodepaths[modelslug] = geomnode
                
                if self.instance_count[modelslug] == 1:
                    geomnode.reparentTo(np)
                else:
                    for instance_np in self.nodepaths_byslug[modelslug]:
                        geomnode.instanceTo(instance_np)
                    self.rigid_body_combiners[modelslug].collect()
                
                if self.showstats:
                    self.num_models_loaded += 1
                    self.update_stats()
                
            elif args[0] == LOAD_TYPE.TEXTURE_UPDATE:
                np, newtex = args[1], args[2]
                np.setTextureOff(1)
                np.setTexture(newtex, 1)
                if self.showstats:
                    self.num_texture_updates += 1
                    self.update_stats()
            elif args[0] == LOAD_TYPE.MESH_REFINEMENT:
                modelslug, pm_refinements = args[1], args[2]
                np = self.unique_nodepaths[modelslug]
                pdae_updater.update_nodepath(np.node(), pm_refinements)
                
                if self.instance_count[modelslug] > 1:
                    self.rigid_body_combiners[modelslug].collect()
                
                if self.showstats:
                    self.num_mesh_refinements += 1
                    self.update_stats()
        
        return task.again

    def trigger_screenshot(self, task):
        if self.start_time is None:
            self.start_time = self.globalClock.getLongTime()
            task.delayTime = 1.0
            return task.again
        
        run_time = self.globalClock.getLongTime() - self.start_time
        fname = ('%07.2f' % run_time) + '.tiff'
        self.screenshot_info.append({'filename': fname,
                                     'position': list(self.cam.getPos()),
                                     'hpr': list(self.cam.getHpr())})
        self.win.saveScreenshot(os.path.join(self.screenshot_dir, 'realtime', fname))
        return task.again

    def finished(self, task):
        if self.screenshot_dir is not None:
            with open(os.path.join(self.screenshot_dir, 'info.json'), 'w') as f:
                json.dump(self.screenshot_info, f, indent=2)
        
            sys.exit(len(self.screenshot_info))
        
        sys.exit(0)

    def update_stats(self):
        self.txtMetadataLoaded.setText('Metadata Loaded: %d/%d' % (self.num_metadata_loaded, len(self.unique_models)))
        self.txtUniqueLoaded.setText('Base Mesh Loaded: %d/%d' % (self.num_models_loaded, len(self.unique_models)))
        self.txtTextureUpdates.setText('Texture Updates: %d/%d' % (self.num_texture_updates, self.total_texture_updates))
        self.txtMeshRefinements.setText('Mesh Refinements: %d/%d' % (self.num_mesh_refinements, self.total_mesh_refinements))
