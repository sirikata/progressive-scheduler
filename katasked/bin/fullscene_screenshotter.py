#!/usr/bin/env python2

import os
import sys
import json
import collections
import math
import time

import argparse
import panda3d.core as p3d
import direct.showbase.ShowBase as ShowBase
import direct.interval.MopathInterval as MopathInterval
import direct.gui as gui
import meshtool.filters.panda_filters.pandacore as pcore
import meshtool.filters.panda_filters.pandacontrols as controls
import meshtool.filters.print_filters.print_pm_perceptual_error as percepfilter

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
import katasked.loader as loader

class FullSceneScreenshotLoader(loader.ProgressiveLoader):
    def __init__(self, scenefile, screenshot_dir):
        loader.ProgressiveLoader.__init__(self, scenefile)
        
        self.dumpdir = screenshot_dir
        info_file = os.path.join(self.dumpdir, 'info.json')
        with open(info_file, 'r') as f:
            self.camera_points = json.load(f)
    
    def run(self):
        self.render.hide()
        while self.multiplexer.empty() != True or len(self.waiting) > 0:
            self.taskMgr.step()
            self.taskMgr.step()
        
        self.render.show()
        
        for camera_pt in self.camera_points:
            fname = camera_pt['filename']
            position = camera_pt['position']
            hpr = camera_pt['hpr']
            self.cam.setPosHpr(*(position + hpr))
            
            self.taskMgr.step()
            self.taskMgr.step()
            
            self.win.saveScreenshot(os.path.join(self.dumpdir, 'groundtruth', fname))

def main():
    parser = argparse.ArgumentParser(description='Fully loads a scene and then captures screenshots based on a previous run of loadscene.py')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
    parser.add_argument('--screenshot-dir', '-d', metavar='directory', required=True,
                        help='Directory where screenshots were dumped and will be dumped')
    
    args = parser.parse_args()
    
    if args.screenshot_dir is not None:
        outdir = os.path.abspath(args.screenshot_dir)
        if os.path.exists(outdir) and not os.path.isdir(outdir):
            parser.error('Invalid screenshots directory: %s' % outdir)
        elif not os.path.exists(os.path.join(outdir, 'groundtruth')):
            os.makedirs(os.path.join(outdir, 'groundtruth'))
    
    app = FullSceneScreenshotLoader(args.scene, outdir)
    app.run()

if __name__ == '__main__':
    main()
