#!/usr/bin/env python2

import os
import json
import argparse
import collections

import numpy
import matplotlib.pyplot as plt
from matplotlib import rc
from matplotlib.font_manager import FontProperties

import pathmangle
import katasked.task.priority as priority

rc('text', usetex=True)
rc('font', family='sans-serif')
rc('font', size='18')

def main():
    parser = argparse.ArgumentParser(description='Graphs the results of priority_experiment_runner.py')
    parser.add_argument('--experiment-dir', '-d', metavar='directory',
                        help='Directory where experiment was output to')
    
    args = parser.parse_args()

    outdir = os.path.abspath(args.experiment_dir)
    if os.path.exists(outdir) and not os.path.isdir(outdir):
        parser.error('Invalid directory: %s' % outdir)
    
    for priority_algo_name in priority.get_priority_algorithm_names():
        if priority_algo_name == 'FromFile':
            continue
        
        algo_class = priority.get_algorithm_by_name(priority_algo_name)
        friendly_name = algo_class.name
        
        algo_dir = os.path.join(outdir, priority_algo_name)
        capdirs = os.listdir(algo_dir)
        for capname in capdirs:
            capdir = os.path.join(algo_dir, capname)
            trial_dirs = os.listdir(capdir)
            
            trial_means = []
            for trial_name in trial_dirs:
                trial_dir = os.path.join(capdir, trial_name)
                if not os.path.exists(os.path.join(trial_dir, 'perceptualdiff.json')):
                    continue
                perceptual_data = json.loads(open(os.path.join(trial_dir, 'perceptualdiff.json'), 'r').read())
                
                times = []
                errvals = []
                for ssdata in perceptual_data:
                    num = float('.'.join(ssdata['filename'].split('.')[:2]))
                    times.append(num)
                    err = ssdata['perceptualdiff']
                    errvals.append(err)
                
                times = numpy.array(times)
                errvals = numpy.array(errvals)
                diffs = numpy.ediff1d(times, to_begin=times[0] - 0)
                mean = numpy.sum(diffs * errvals) / times[-1]
                trial_means.append(mean)
                
            print priority_algo_name, capname, ['%.7g' % v for v in trial_means]
    
    import sys
    sys.exit(0)
    
    times = collections.defaultdict(list)
    errvals = collections.defaultdict(list)
    for exp, _ in dirs:
        e = os.path.join(ROOT, exp, 'perceptualdiff.json')
        with open(e, 'r') as f:
            error_data = json.load(f)
            for err in error_data:
                num = float('.'.join(err['filename'].split('.')[:2]))
                times[exp].append(num)
                errvals[exp].append(err['perceptualdiff'])
    
    fig = plt.figure(figsize=(11.5, 8))
    ax1 = fig.add_subplot(111)
    
    means = [(numpy.mean(numpy.array(err)), key) for key, err in errvals.iteritems()]
    means = sorted(means, reverse=True)
    exporder = [m[1] for m in means]
    
    colors = iter(['b', 'r', 'g', 'k', 'y', 'b', 'r', 'g'])
    markers = iter(['h', 's', 'v', 'o', '^', 'v', 'o', '^'])
    means = {}
    for exp in exporder:
        x = numpy.array(times[exp])
        y = numpy.array(errvals[exp])
        diffs = numpy.ediff1d(x, to_begin=x[0] - 0)
        mean = numpy.sum(diffs * y) / x[-1]
        means[exp] = mean
        y[y < 1] = 1
        ax1.plot(x, y, c=next(colors), marker=next(markers), linewidth=2)
    
    #ax1.set_yscale('log')
    
    sorted_means = sorted(means.iteritems(), key=lambda e: e[1])
    dirdict = dict(dirs)
    for exp, mean in sorted_means:
        print '%s    %.4g' % (dirdict[exp].rjust(20), mean / max(means.values()))
    
    prop = FontProperties(size=12)
    plt.legend([dirdict[e] for e in exporder], loc=1, prop=prop)
    plt.ylabel('Perceptual Error (pixels)')
    plt.xlabel('Time (s)')
    plt.title('Perceptual Error by Priority Algorithm')
    plt.savefig('fig.pdf')

if __name__ == '__main__':
    main()
