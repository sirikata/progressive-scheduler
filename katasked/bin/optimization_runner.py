#!/usr/bin/env python2

import os
import collections
import json
import subprocess
import shutil
import tempfile
import collada

import argparse
import numpy
import scipy.optimize

import pathmangle
import katasked.util as util

CURDIR = os.path.abspath(os.path.dirname(__file__))
LOADSCENE = os.path.join(CURDIR, 'loadscene.py')
FULLSCENE_SCREENSHOTTER = os.path.join(CURDIR, 'fullscene_screenshotter.py')
PERCEPTUAL_DIFFER = os.path.join(CURDIR, 'perceptual_differ.py')

INITIAL_GUESS = collections.OrderedDict([
    ("solid_angle", 1.0),
    ("future_5_solid_angle", 1.0),
    ("camera_angle", 1.0),
    ("future_5_camera_angle", 1.0),
    ("perceptual_error", 1.0),
])

def call(*args, **kwargs):
    print 'Executing', ' '.join(args[0])
    return subprocess.call(*args, **kwargs)

iteration_num = 0

def main():
    parser = argparse.ArgumentParser(description=('Runs scipy.minimize function, trying to minimize percept error '
                                                  'where each iteration runs loadscene.py, fullscene_screenshotter.py, '
                                                  'and perceptual_differ.py'))
    
    parser.add_argument('--screenshot-dir', metavar='directory', required=True,
                        help='Root directory where screenshot subdirectories will be created. Each iteration will be saved.')
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
    
    def iteration(x):
        global iteration_num
        iteration_num += 1
        
        new_guess = {}
        for i, varname in enumerate(INITIAL_GUESS.keys()):
            new_guess[varname] = x[i]
        
        temp_json_fname = tempfile.mktemp(suffix=".json", prefix="opt-iteration-vars")
        tempdir = tempfile.mkdtemp(prefix="katasked-exp-tempcache")
        
        expdir = os.path.join(screenshot_dir, "%.7d" % iteration_num)
        if not os.path.isdir(expdir):
            os.mkdir(expdir)
        
        iteration_info_fname = os.path.join(expdir, 'iteration.json')
        
        if not os.path.isfile(iteration_info_fname):
            
            try:
                
                print 'guessing:', ', '.join('%s:%.7g' % (k,v) for k,v in new_guess.iteritems())
                
                with open(temp_json_fname, 'w') as f:
                    json.dump(new_guess, f)
                
                call([LOADSCENE,
                     '--capture', motioncap_file,
                     '--scene', scene_file,
                     '--dump-screenshot', expdir,
                     '--cache-dir', tempdir,
                     '--priority-algorithm', 'FromFile',
                     '--priority-input', temp_json_fname])
            
            finally:
                try:
                    os.remove(temp_json_fname)
                except OSError:
                    pass
                
                shutil.rmtree(tempdir, ignore_errors=True)
    
            call([FULLSCENE_SCREENSHOTTER,
                  '--scene', scene_file,
                  '--cache-dir', fullcache_dir,
                  '--priority-algorithm', 'Random',
                  '-d', expdir])
            
            call([PERCEPTUAL_DIFFER,
                  '-d', expdir])
            
            perceptual_diff_file = os.path.join(expdir, 'perceptualdiff.json')
            with open(perceptual_diff_file, 'r') as f:
                perceptual_data = json.load(f)
            
            times = []
            errors = []
            for fdata in perceptual_data:
                errors.append(fdata['perceptualdiff'])
                times.append(float('.'.join(fdata['filename'].split('.')[:2])))
            
            times = numpy.array(times)
            errors = numpy.array(errors)
            diffs = numpy.ediff1d(times, to_begin=times[0] - 0)
            mean = numpy.sum(errors * diffs) / times[-1]
            
            with open(iteration_info_fname, 'w') as f:
                json.dump({'mean': mean,
                           'inputs': new_guess}, f, indent=2)
        
        with open(iteration_info_fname, 'r') as f:
            iteration_data = json.load(f)
            previous_inputs = iteration_data['inputs']
            for varname, value in previous_inputs.iteritems():
                assert collada.util.falmostEqual(value, new_guess[varname])
            print '==> Iteration %i result %.7g' % (iteration_num, iteration_data['mean'])
            return iteration_data['mean']
    
    res = scipy.optimize.minimize(iteration, INITIAL_GUESS.values(), method='BFGS')
    print 'answer', res.x

if __name__ == '__main__':
    main()
