#!/usr/bin/env python2

import os
import json
import subprocess
import shutil
import tempfile

import argparse

import pathmangle
import katasked.util as util
import katasked.task.priority as priority

CURDIR = os.path.abspath(os.path.dirname(__file__))
LOADSCENE = os.path.join(CURDIR, 'loadscene.py')
FULLSCENE_SCREENSHOTTER = os.path.join(CURDIR, 'fullscene_screenshotter.py')
PERCEPTUAL_DIFFER = os.path.join(CURDIR, 'perceptual_differ.py')

def main():
    parser = argparse.ArgumentParser(description=('Runs an experiment for each priority algorithm registered, generating screenshots '
                                                  'for each. Then runs fullscene_screenshotter to capture the ground truth. Then runs '
                                                  'perceptual_differ to generate result data.'))
    parser.add_argument('--screenshot-dir', metavar='directory', required=True,
                        help='Root directory where screenshot subdirectories will be created')
    parser.add_argument('--full-cache-dir', metavar='directory', required=True,
                        help='Cache directory to use for fullscene_screenshotter')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'), required=True,
                        help='File of the motion capture to use for the camera.')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
    
    args = parser.parse_args()
    
    motioncap_file = os.path.abspath(args.capture.name)
    args.capture.close()
    scene_file = os.path.abspath(args.scene.name)
    args.scene.close()

    screenshot_dir = os.path.abspath(args.screenshot_dir)
    if not os.path.isdir(screenshot_dir):
        os.mkdir(screenshot_dir)
    
    fullcache_dir = os.path.abspath(args.full_cache_dir)
    if not os.path.isdir(fullcache_dir):
        os.mkdir(fullcache_dir)
    
    expdirs = []
    for expname in priority.get_priority_algorithm_names():
        expdir = os.path.join(screenshot_dir, expname)
        if not os.path.isdir(expdir):
            os.mkdir(expdir)
        expdirs.append(expdir)
        
        tempdir = tempfile.mkdtemp(prefix="katasked-exp-tempcache")
        try:
            subprocess.call([LOADSCENE,
                             '--capture', motioncap_file,
                             '--scene', scene_file,
                             '--dump-screenshot', expdir,
                             '--cache-dir', tempdir,
                             '--priority-algorithm', expname])
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)
    
    command = [FULLSCENE_SCREENSHOTTER,
               '--scene', scene_file,
               '--cache-dir', fullcache_dir,
               '--priority-algorithm', 'Random']
    for expdir in expdirs:
        command.extend(['-d', expdir])
    subprocess.call(command)
    
    command = [PERCEPTUAL_DIFFER]
    for expdir in expdirs:
        command.extend(['-d', expdir])
    subprocess.call(command)

if __name__ == '__main__':
    main()
