#!/usr/bin/env python2

import sys
import json
import collections
import time

import argparse
import panda3d.core as p3d
import direct.showbase.ShowBase as ShowBase
import direct.interval.MopathInterval as MopathInterval
import meshtool.filters.panda_filters.pandacore as pcore
import meshtool.filters.panda_filters.pandacontrols as controls

import pathmangle
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

class SceneLoader(ShowBase.ShowBase):
    
    def __init__(self, capturefile, scenefile):
        
        self.scenefile = scenefile
        self.scene = scene.Scene.fromfile(scenefile)
        self.unique_models = set(m.slug for m in self.scene)
        print '%d objects in scene, %d unique' % (len(self.scene), len(self.unique_models))
        
        # turns on lazy loading of textures
        p3d.loadPrcFileData('', 'preload-textures 0')
        p3d.loadPrcFileData('', 'preload-simple-textures 1')
        p3d.loadPrcFileData('', 'compressed-textures 0')
        p3d.loadPrcFileData('', 'allow-incomplete-render 1')
        
        # window size to 1024x768
        p3d.loadPrcFileData('', 'win-size 1024 768')
        
        ShowBase.ShowBase.__init__(self)
        
        # create a nodepath for each unique model
        self.unique_nodepaths = dict((m, p3d.NodePath(m)) for m in self.unique_models)
        
        # find out how many objects are going to be instanced for each node
        self.instance_count = collections.defaultdict(int)
        for model in self.scene:
            self.instance_count[model.slug] += 1
        
        # then instance each unique model to its instantiation in the actual scene
        self.nodepaths = {}
        for model in self.scene:
            unique_np = self.unique_nodepaths[model.slug]
            node_name = model.slug + "_%.7g_%.7g_%.7g" % (model.x, model.y, model.z)
            
            if self.instance_count[model.slug] == 1:
                unique_np.setName(node_name)
                unique_np.reparentTo(self.render)
                np = unique_np
            else:
                np = self.render.attachNewNode(node_name)
                unique_np.instanceTo(np)
            
            self.nodepaths[model] = np
            np.setPos(model.x, model.y, model.z)
            np.setScale(model.scale, model.scale, model.scale)
            q = p3d.Quat()
            q.setI(model.orient_x)
            q.setJ(model.orient_y)
            q.setK(model.orient_z)
            q.setR(model.orient_w)
            np.setQuat(q)
        
        self.waiting = []
        self.pm_waiting = collections.defaultdict(list)
        self.models_loaded = set()
        self.loading_priority = 2147483647
        
        self.pandastate = katasked.panda.PandaState(self.cam, self.unique_nodepaths, self.nodepaths)
        self.multiplexer = pool.MultiplexPool(2)
        
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
        
        if capturefile is not None:
            self.capturefile = capturefile
            self.capturedata = json.load(self.capturefile)
            self.duration = self.capturedata['duration']
            self.positions = self.capturedata['positions']
            self.rotations = self.capturedata['rotations']
            
            self.curve_creator = motioncap.CreateNurbsCurve()
            for pos, rot in zip(self.positions, self.rotations):
                self.curve_creator.addPoint(pos, rot)
            self.mopath = self.curve_creator.getMotionPath()
            
            self.interval = MopathInterval.MopathInterval(self.mopath, self.cam, duration=self.duration, name="Camera Replay")
            self.interval.start()
        else:
            controls.KeyboardMovement()
            controls.MouseCamera()
        
    def run(self):
        self.update_priority_task = self.taskMgr.doMethodLater(0.2, self.check_pool, 'check_pool')
        self.load_waiting_task = self.taskMgr.doMethodLater(0.3, self.load_waiting, 'load_waiting')
        
        ShowBase.ShowBase.run(self)
        
    def check_pool(self, task):
        finished_tasks = self.multiplexer.poll(self.pandastate)
        
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
                
            self.loading_priority -= 1
        
        return task.again

    def model_loaded(self, modelpath, modelslug):
        np = self.unique_nodepaths[modelslug]
        self.models_loaded.add(modelslug)
        self.waiting.append((LOAD_TYPE.INITIAL_MODEL, modelpath, np))
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
                modelpath, np = args[1], args[2]
                modelpath.reparentTo(np)
            elif args[0] == LOAD_TYPE.TEXTURE_UPDATE:
                np, newtex = args[1], args[2]
                texnp = np.find("**/primitive")
                texnp.setTextureOff(1)
                texnp.setTexture(newtex, 1)
            elif args[0] == LOAD_TYPE.MESH_REFINEMENT:
                modelslug, pm_refinements = args[1], args[2]
                np = self.unique_nodepaths[modelslug]
                toupdate = np.find("**/primitive")
                pdae_updater.update_nodepath(toupdate.node(), pm_refinements)
        
        return task.again

def main():
    parser = argparse.ArgumentParser(description='Progressively loads a scene')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'),
                        help='File of the motion capture to use for the camera. If not specified, keyboard and mouse controls are enabled.')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
    
    args = parser.parse_args()
    
    app = SceneLoader(args.capture, args.scene)
    app.run()

if __name__ == '__main__':
    main()
