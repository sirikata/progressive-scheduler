#!/usr/bin/env python2

import sys
import json

import argparse
import panda3d.core as p3d
import direct.showbase.ShowBase as ShowBase
import direct.interval.MopathInterval as MopathInterval
import meshtool.filters.panda_filters.pandacore as pcore

import pathmangle
import katasked.scene as scene
import katasked.motioncap as motioncap

class SceneLoader(ShowBase.ShowBase):
    
    def __init__(self, capturefile, scenefile):
        
        self.capturefile = capturefile
        self.capturedata = json.load(self.capturefile)
        self.duration = self.capturedata['duration']
        self.positions = self.capturedata['positions']
        self.rotations = self.capturedata['rotations']
        
        self.curve_creator = motioncap.CreateNurbsCurve()
        for pos, rot in zip(self.positions, self.rotations):
            self.curve_creator.addPoint(pos, rot)
        self.mopath = self.curve_creator.getMotionPath()
        
        self.scenefile = scenefile
        self.scene = scene.Scene.fromfile(scenefile)
        self.unique_models = set(m.slug for m in self.scene)
        print '%d objects in scene, %d unique' % (len(self.scene), len(self.unique_models))
        
        ShowBase.ShowBase.__init__(self)
        
        # create a nodepath for each unique model
        self.unique_nodepaths = dict((m, p3d.NodePath(m)) for m in self.unique_models)
        
        # then instance each unique model to its instantiation in the actual scene
        self.nodepaths = {}
        for model in self.scene:
            unique_np = self.unique_nodepaths[model.slug]
            np = self.render.attachNewNode(model.slug + "_%.7g_%.7g_%.7g" % (model.x, model.y, model.z))
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
        
        self.disableMouse()
        pcore.attachLights(self.render)
        self.render.setShaderAuto()
        self.render.setTransparency(p3d.TransparencyAttrib.MNone)
        
        self.camLens.setFar(sys.maxint)
        self.camLens.setNear(8.0)
        self.render.setAntialias(p3d.AntialiasAttrib.MAuto)
        
        self.interval = MopathInterval.MopathInterval(self.mopath, self.cam, duration=self.duration, name="Camera Replay")
        self.interval.start()
        
    def run(self):
        ShowBase.ShowBase.run(self)

def main():
    parser = argparse.ArgumentParser(description='Progressively loads a scene')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'), required=True,
                        help='file of the motion capture to use for the camera')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='scene file to render')
    
    args = parser.parse_args()
    
    app = SceneLoader(args.capture, args.scene)
    app.run()

if __name__ == '__main__':
    main()
