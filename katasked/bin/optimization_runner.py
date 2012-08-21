#!/usr/bin/env python2

import os
import collections
import json
import time
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
    ("future_2_solid_angle", 1.0),
    ("camera_angle", 1.0),
    ("future_2_camera_angle", 1.0),
    ("future_5_camera_angle", 1.0),
    ("perceptual_error", 1.0),
])

def call(*args, **kwargs):
    print 'Executing', ' '.join(args[0])
    start_time = time.time()
    timeout = kwargs.pop('timeout', None)
    p = subprocess.Popen(*args, **kwargs)
    while p.poll() is None:
        t = time.time()
        if timeout is not None and t - start_time > timeout:
            p.kill()
            return None
        time.sleep(1)
    return p.poll()

iteration_num = 0

TRIALS = 3

def main():
    parser = argparse.ArgumentParser(description=('Runs scipy.minimize function, trying to minimize percept error '
                                                  'where each iteration runs loadscene.py, fullscene_screenshotter.py, '
                                                  'and perceptual_differ.py'))
    
    parser.add_argument('--screenshot-dir', metavar='directory', required=True,
                        help='Root directory where screenshot subdirectories will be created. Each iteration will be saved.')
    parser.add_argument('--full-cache-dir', metavar='directory', required=True,
                        help='Cache directory to use for fullscene_screenshotter')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'), default=list(), action='append',
                        help='File of the motion capture to use for the camera.')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
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
    
    def iteration(x):
        global iteration_num
        iteration_num += 1
        
        new_guess = {}
        for i, varname in enumerate(INITIAL_GUESS.keys()):
            new_guess[varname] = x[i]
        
        temp_json_fname = tempfile.mktemp(suffix=".json", prefix="opt-iteration-vars")
        
        expdir = os.path.join(screenshot_dir, "%.7d" % iteration_num)
        if not os.path.isdir(expdir):
            os.mkdir(expdir)
        
        iteration_info_fname = os.path.join(expdir, 'iteration.json')
        
        if not os.path.isfile(iteration_info_fname):
            
            print 'guessing:', ', '.join('%s:%f' % (k,v) for k,v in new_guess.iteritems())
            
            expdirs = []
            for motioncap_filename in motioncap_filenames:
            
                motioncap_duration = json.loads(open(motioncap_filename, 'r').read())['duration']
                
                for trial_num in range(TRIALS):
                    
                    trial_expdir = os.path.join(expdir, os.path.basename(motioncap_filename), 'trial_%d' % trial_num)
                    if not os.path.isdir(trial_expdir):
                        os.makedirs(trial_expdir)
                    expdirs.append(trial_expdir)
                    
                    if os.path.exists(os.path.join(trial_expdir, 'info.json')):
                        num_screenshots = len(json.loads(open(os.path.join(trial_expdir, 'info.json'), 'r').read()))
                        if num_screenshots >= 0.6 * motioncap_duration:
                            print 'Skipping loadscene for', expdir
                            continue
                        else:
                            print 'Running again because only found', num_screenshots, 'screenshots for a', motioncap_duration, 'motion duration'
                    
                    tempdir = tempfile.mkdtemp(prefix="katasked-exp-tempcache")
                    
                    try:
                        
                        with open(temp_json_fname, 'w') as f:
                            json.dump(new_guess, f)
                        
                        command = [LOADSCENE,
                                   '--capture', motioncap_filename,
                                   '--scene', scene_file,
                                   '--dump-screenshot', trial_expdir,
                                   '--cache-dir', tempdir,
                                   '--priority-algorithm', 'FromFile',
                                   '--priority-input', temp_json_fname]
                        
                        if args.cdn_domain is not None:
                            command.extend(['--cdn-domain', args.cdn_domain])
                        
                        retcode = None
                        while retcode is None or retcode < 0.6 * motioncap_duration:
                            retcode = call(command, timeout=2*motioncap_duration)
                            if retcode is None:
                                print
                                print '====='
                                print 'ERROR: loadscene timed out!'
                                print '====='
                                print
                            elif retcode < 0.6 * motioncap_duration:
                                print
                                print '====='
                                print 'ERROR: loadscene is not doing well. it only took', retcode, 'screenshots out of expected', motioncap_duration
                                print trial_expdir
                                print '====='
                                print
                    
                    finally:
                        try:
                            os.remove(temp_json_fname)
                        except OSError:
                            pass
                        
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
                    info_data = json.loads(open(os.path.join(expdir, 'info.json'), 'r').read())
                    need_filenames = set([i['filename'] for i in info_data])
                    try:
                        groundtruth_files = set(os.listdir(os.path.join(expdir, 'groundtruth')))
                    except OSError:
                        groundtruth_files = set()
                    
                    if need_filenames.issubset(groundtruth_files):
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
            
            perceptual_datas = []
            exp_means = []
            for expdir in expdirs:
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
                exp_means.append(mean)
                
            with open(iteration_info_fname, 'w') as f:
                json.dump({'means': exp_means,
                           'mean': sum(exp_means) / float(len(exp_means)),
                           'inputs': new_guess}, f, indent=2)
        
        with open(iteration_info_fname, 'r') as f:
            iteration_data = json.load(f)
            previous_inputs = iteration_data['inputs']
            for varname, value in previous_inputs.iteritems():
                assert collada.util.falmostEqual(value, new_guess[varname])
            print '==> Iteration %i' % iteration_num, 'inputs', ','.join('%g' % v for k,v in new_guess.iteritems())
            print '==> Iteration %i result %.7g' % (iteration_num, iteration_data['mean'])
            return iteration_data['mean']
    
    res = scipy.optimize.minimize(iteration, INITIAL_GUESS.values(), method='BFGS')
    print 'answer', res.x

if __name__ == '__main__':
    main()
