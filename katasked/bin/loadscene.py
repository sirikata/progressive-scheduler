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

def main():
    parser = argparse.ArgumentParser(description='Progressively loads a scene')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'),
                        help='File of the motion capture to use for the camera. If not specified, keyboard and mouse controls are enabled.')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
    parser.add_argument('--show-stats', action='store_true', default=False,
                        help='Display on-screen statistics about scene while loading')
    parser.add_argument('--dump-screenshot', '-d', metavar='directory', help='Directory to dump screenshots to')
    
    args = parser.parse_args()
    
    outdir = None
    if args.dump_screenshot is not None:
        outdir = os.path.abspath(args.dump_screenshot)
        if os.path.exists(outdir) and not os.path.isdir(outdir):
            parser.error('Invalid screenshots directory: %s' % outdir)
        elif not os.path.exists(os.path.join(outdir, 'realtime')):
            os.makedirs(os.path.join(outdir, 'realtime'))
    
    app = loader.ProgressiveLoader(args.scene,
                                   capturefile=args.capture,
                                   showstats=args.show_stats,
                                   screenshot_dir=outdir)
    app.run()

if __name__ == '__main__':
    main()
