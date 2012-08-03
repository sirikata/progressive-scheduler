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
import katasked.panda
import katasked.motioncap as motioncap

class MotionReplay(ShowBase.ShowBase):
    
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
        
        terrain = [m for m in self.scene if m.model_type == 'terrain']
        assert len(terrain) == 1
        terrain = terrain[0]
        
        mesh = terrain.mesh
        np = katasked.panda.mesh_to_nodepath(mesh)
        
        ShowBase.ShowBase.__init__(self)
        
        np.reparentTo(self.render)
        np.setPos(terrain.x, terrain.y, terrain.z)
        np.setScale(terrain.scale, terrain.scale, terrain.scale)
        q = p3d.Quat()
        q.setI(terrain.orient_x)
        q.setJ(terrain.orient_y)
        q.setK(terrain.orient_z)
        q.setR(terrain.orient_w)
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
        
        print
        print '==========='
        print 'Replaying motion path for', self.duration, 'seconds'
        print '==========='
        print
        
        self.taskMgr.doMethodLater(self.duration + 3.0, sys.exit, 'exiter')
        

def main():
    parser = argparse.ArgumentParser(description='Replays a motion path for a scene')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'), required=True,
                        help='file of the motion capture to replay')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='scene file to render during capture (only terrain is displayed)')
    
    args = parser.parse_args()
    
    app = MotionReplay(args.capture, args.scene)
    app.run()

if __name__ == '__main__':
    main()
