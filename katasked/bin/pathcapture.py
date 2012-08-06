#!/usr/bin/env python2

import sys
import json
import argparse
import panda3d.core as p3d
import direct.showbase.ShowBase as ShowBase
import meshtool.filters.panda_filters.pandacore as pcore
import meshtool.filters.panda_filters.pandacontrols as controls

import pathmangle
import katasked.scene as scene
import katasked.panda

class MotionCapture(ShowBase.ShowBase):
    
    def __init__(self, outfile, scenefile):
        
        self.outfile = outfile
        self.scenefile = scenefile
        self.scene = scene.Scene.fromfile(scenefile)
        
        terrain = [m for m in self.scene if m.model_type == 'terrain']
        assert len(terrain) == 1
        terrain = terrain[0]
        
        mesh = terrain.mesh
        np = katasked.panda.mesh_to_nodepath(mesh)
        
        ShowBase.ShowBase.__init__(self)
        
        print
        print '==========='
        print 'Use w-s-a-d keys to move, arrow keys or right-click-drag to move camera.'
        print 'Press enter when ready to start capturing.'
        print '==========='
        print
        
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
        
        controls.KeyboardMovement()
        controls.MouseCamera()
        
        self.positions = []
        self.rotations = []
        
        self.acceptOnce('enter', self.startCapture)

    def capturePoints(self, task):
        pos = self.cam.getPos()
        hpr = self.cam.getHpr()
        self.positions.append(tuple(pos))
        self.rotations.append(tuple(hpr))
        return task.again
    
    def startCapture(self):
        print 'Starting motion capture. Press enter when ready to stop.'
        self.capTask = self.taskMgr.doMethodLater(0.2, self.capturePoints, 'capturePoints')
        self.acceptOnce('enter', self.finishCapture)
    
    def finishCapture(self):
        self.taskMgr.remove(self.capTask)
        self.elapsed_time = p3d.ClockObject.getGlobalClock().getFrameTime()
        print 'Captured', len(self.positions), 'camera positions over', self.elapsed_time
        
        json_out = {'positions': self.positions,
                   'rotations': self.rotations,
                   'duration': self.elapsed_time}
        
        json.dump(json_out, self.outfile, indent=2)
        
        print 'Motion capture JSON dumped to %s.' % self.outfile.name
        sys.exit(0)
        

def parse_point3(s):
    vals = s.split(',')
    try:
        vals = [float(v) for v in vals]
        if len(vals) != 3:
            raise ValueError()
        return p3d.Point3(*vals)
    except ValueError:
        raise argparse.ArgumentTypeError("invalid format for point3")

def parse_hpr(s):
    p3 = parse_point3(s)
    if not all(-180.0 <= p <= 180.0 for p in p3):
        raise argparse.ArgumentTypeError("invalid angle range for rotation")
    return p3

def main():
    parser = argparse.ArgumentParser(description='Captures a motion path for a scene into a file')
    parser.add_argument('--out', '-o', metavar='motioncap.json', type=argparse.FileType('w'), required=True,
                        help='file to save motion path to')
    parser.add_argument('--scene', '--in', '-i', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='scene file to render during capture (only terrain is displayed)')
    
    args = parser.parse_args()
    
    app = MotionCapture(args.out, args.scene)
    app.run()

if __name__ == '__main__':
    main()
