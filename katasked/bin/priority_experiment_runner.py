#!/usr/bin/env python2

import os
import sys
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

def call(*args, **kwargs):
    print 'Executing', ' '.join(args[0])
    return subprocess.call(*args, **kwargs)

def main():
    parser = argparse.ArgumentParser(description=('Runs an experiment for each priority algorithm registered, generating screenshots '
                                                  'for each. Then runs fullscene_screenshotter to capture the ground truth. Then runs '
                                                  'perceptual_differ to generate result data.'))
    parser.add_argument('--screenshot-dir', metavar='directory', required=True,
                        help='Root directory where screenshot subdirectories will be created')
    parser.add_argument('--full-cache-dir', metavar='directory', required=True,
                        help='Cache directory to use for fullscene_screenshotter')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'), action='append', required=True,
                        help='File of the motion capture to use for the camera.')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
    parser.add_argument('--iterations', type=int, default=3, help='Number of iterations per experiment')
    parser.add_argument('--cdn-domain', metavar='example.com')
    
    args = parser.parse_args()
    
    scene_file = os.path.abspath(args.scene.name)
    args.scene.close()
    
    screenshot_dir = os.path.abspath(args.screenshot_dir)
    if not os.path.isdir(screenshot_dir):
        os.mkdir(screenshot_dir)
    
    fullcache_dir = os.path.abspath(args.full_cache_dir)
    if not os.path.isdir(fullcache_dir):
        os.mkdir(fullcache_dir)
    
    motioncap_filenames = []
    for motioncap_file in args.capture:
        motioncap_filename = os.path.abspath(motioncap_file.name)
        motioncap_file.close()
        motioncap_filenames.append(motioncap_filename)
    
    
    expdirs = []
    for priority_algo_name in priority.get_priority_algorithm_names():
        
        if priority_algo_name == 'FromFile':
            continue
        
        for motioncap_filename in motioncap_filenames:
            
            motioncap_duration = json.loads(open(motioncap_filename, 'r').read())['duration']
        
            for iteration_num in range(args.iterations):
                
                # ssdir/motioncap.json/0000001/algo/
                expdir = os.path.join(screenshot_dir, priority_algo_name, os.path.basename(motioncap_filename), "%.7d" % iteration_num)
                expdirs.append(expdir)
                
                if os.path.exists(os.path.join(expdir, 'info.json')):
                    num_screenshots = len(json.loads(open(os.path.join(expdir, 'info.json'), 'r').read()))
                    if num_screenshots >= 0.6 * motioncap_duration:
                        print 'Skipping loadscene for', expdir
                        continue
                    else:
                        print 'Running again because only found', num_screenshots, 'screenshots for a', motioncap_duration, 'motion duration'
                
                if not os.path.isdir(expdir):
                    os.makedirs(expdir)
                
                tempdir = tempfile.mkdtemp(prefix="katasked-exp-tempcache")
                try:
                    command = [LOADSCENE,
                               '--capture', motioncap_filename,
                               '--scene', scene_file,
                               '--dump-screenshot', expdir,
                               '--cache-dir', tempdir,
                               '--priority-algorithm', priority_algo_name]
                    
                    if args.cdn_domain is not None:
                        command.extend(['--cdn-domain', args.cdn_domain])
                    
                    retcode = call(command)
                    if retcode < 0.6 * motioncap_duration:
                        print
                        print '====='
                        print 'ERROR: loadscene is not doing well. it only took', retcode, 'screenshots out of expected', motioncap_duration
                        print expdir
                        print '====='
                        print
                        sys.exit(-1)
                    
                finally:
                    shutil.rmtree(tempdir, ignore_errors=True)
    
    
    command = [FULLSCENE_SCREENSHOTTER,
               '--scene', scene_file,
               '--cache-dir', fullcache_dir,
               '--priority-algorithm', 'Random']
    
    if args.cdn_domain is not None:
        command.extend(['--cdn-domain', args.cdn_domain])
    
    retcode = -1
    
    while retcode != 0:
        for expdir in expdirs:
            realtime_files = set(os.listdir(os.path.join(expdir, 'realtime')))
            try:
                groundtruth_files = set(os.listdir(os.path.join(expdir, 'groundtruth')))
            except OSError:
                groundtruth_files = set()
            
            if realtime_files == groundtruth_files:
                print 'Skipping fullscene_screenshotter for', expdir
                continue
            
            command.extend(['-d', expdir])
        
        retcode = call(command)
    
    
    command = [PERCEPTUAL_DIFFER]
    
    for expdir in expdirs:
        if os.path.exists(os.path.join(expdir, 'perceptualdiff.json')):
            print 'Skipping perceptualdiff for', expdir
            continue
        command.extend(['-d', expdir])
    
    if len(command) > 1:
        call(command)

if __name__ == '__main__':
    main()
