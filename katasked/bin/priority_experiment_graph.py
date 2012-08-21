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
    parser.add_argument('--experiment-dir', '-d', metavar='directory', required=True,
                        help='Directory where experiment was output to')
    parser.add_argument('--output-dir', '-o', metavar='directory', required=True,
                        help='Directory where graphs should be output to')
    
    args = parser.parse_args()

    outdir = os.path.abspath(args.experiment_dir)
    if os.path.exists(outdir) and not os.path.isdir(outdir):
        parser.error('Invalid directory: %s' % outdir)
    
    graphdir = os.path.abspath(args.output_dir)
    if os.path.exists(graphdir) and not os.path.isdir(graphdir):
        parser.error('Invalid directory: %s' % outdir)
    if not os.path.exists(graphdir):
        os.mkdir(graphdir)
    
    algo_means = collections.defaultdict(list)
    algo_motion_means = collections.defaultdict(dict)
    
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
            algo_motion_means[friendly_name][capname] = trial_means
            algo_means[friendly_name].extend(trial_means)
    
    algo_results = [(numpy.mean(vals), name) for name, vals in algo_means.iteritems()]
    
    print
    print 'Absolute values'
    print '==============='
    for mean, name in sorted(algo_results, reverse=True):
        print '%s    %0.7g' % (name.rjust(20), mean)
    
    print
    print 'Normalized'
    print '=========='
    for mean, name in sorted(algo_results, reverse=True):
        print '%s    %.4g' % (name.rjust(20), mean / max(dict(algo_results).keys()))
    
    print
    print 'As percentage of image size'
    print '==========================='
    for mean, name in sorted(algo_results, reverse=True):
        print '%s    %s %%' % (name.rjust(20), ('%0.1f' % ((mean / (1024 * 768)) * 100)).rjust(4))
    
    positions = numpy.arange(len(algo_results)) + 0.1
    names = []
    percentages = []
    for mean, name in sorted(algo_results):
        names.append(name)
        percentages.append((mean / (1024 * 768)) * 100)
    
    fig = plt.figure(figsize=(11.5, 8))
    ax1 = fig.add_subplot(111)
    
    rects = ax1.bar(positions, percentages, color='white', edgecolor='grey', hatch='//')
    
    def autolabel(rects, labels):
        maxheight = max(rect.get_height() for rect in rects)
        for rect, label in zip(rects, labels):
            height = rect.get_height()
            plt.text(rect.get_x() + rect.get_width() / 2.0, height + maxheight * 0.05, label,
                    ha='center', va='bottom', rotation=90)
            plt.text(rect.get_x() + rect.get_width() / 2.0, height - maxheight * 0.07, '%0.1f' % rect.get_height(),
                    ha='center', va='bottom', clip_on=True)
    
    autolabel(rects, names)
    
    ax1.get_xaxis().set_visible(False)
    ax1.yaxis.set_ticks_position('left')
    plt.yticks(range(0, 101, 10))
    plt.ylabel('Average perceptual error (percentage of screen size)')
    plt.ylim((0, 100))
    plt.title('Perceptual Error by Priority Algorithm')
    plt.subplots_adjust(left=0.08, right=0.96, top=0.94, bottom=0.04)
    plt.savefig(os.path.join(graphdir, 'algo-percentages-bar.pdf'))
    
    
    
    
    fig = plt.figure(figsize=(11.5, 8))
    ax1 = fig.add_subplot(111)
    
    positions = numpy.arange(len(algo_results)) + 0.1
    bar_width = 0.1
    algo_order = [name for mean, name in sorted(algo_results)]
    colors = iter(['b', 'r', 'g', 'k', 'y', 'b', 'r', 'g'])
    
    cap_means = {}
    cap_percentages = {}
    for capname in capdirs:
        percentages = []
        for algo_name in algo_order:
            percentages.append((numpy.mean(algo_motion_means[algo_name][capname]) / (1024 * 768)) * 100)
        cap_percentages[capname] = percentages
        cap_means[capname] = numpy.mean(percentages)
    
    caps_sorted = sorted((capname, mean) for mean, capname in cap_means.iteritems())
    caporder = [capname for mean, capname in caps_sorted]
    
    rects = []
    for i, capname in enumerate(caporder):
        rects.append(ax1.bar(positions + bar_width*i, cap_percentages[capname], bar_width, color=next(colors)))
    
    def autolabel2(rects, labels):
        maxheight = max(rect.get_height() for rect in rects)
        for rect, label in zip(rects, labels):
            height = rect.get_height()
            plt.text(rect.get_x() + rect.get_width() / 2.0, height + maxheight * 0.2, label,
                    ha='center', va='bottom', rotation=90)
    
    autolabel2(rects[1], algo_order)
    
    ax1.get_xaxis().set_visible(False)
    ax1.yaxis.set_ticks_position('left')
    plt.yticks(range(0, 101, 10))
    plt.ylabel('Average perceptual error (percentage of screen size)')
    plt.ylim((0, 100))
    plt.title('Perceptual Error by Priority Algorithm and Motion Path')
    prop = FontProperties(size=12)
    plt.legend([c[8:-5] for c in caporder], loc=2, prop=prop, ncol=7, frameon=False, handlelength=1, columnspacing=1, handletextpad=0.5)
    plt.subplots_adjust(left=0.08, right=0.96, top=0.94, bottom=0.04)
    plt.savefig(os.path.join(graphdir, 'algo-percentages-motion-bars.pdf'))

if __name__ == '__main__':
    main()
