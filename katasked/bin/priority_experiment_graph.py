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
    algo_rawdata = collections.defaultdict(dict)
    algo_motion_means = collections.defaultdict(dict)
    
    for priority_algo_name in priority.get_priority_algorithm_names():
        if priority_algo_name in ('FromFile', 'HandTuned1', 'SinglePerceptualErrorSAng', 'SinglePerceptualErrorScale'):
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
                
                if capname not in algo_rawdata[priority_algo_name]:
                    algo_rawdata[priority_algo_name][capname] = []
                algo_rawdata[priority_algo_name][capname].append({'times': times,
                                                                  'errvals': errvals})
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
    
    
    individual_wanted = ['Random',
                         'SingleCameraAngleExp',
                         'SingleScale',
                         'OptimizationResult',
                         'SingleSolidAngle',
                         'SingleDistance'
                         ]
    
    H = [
     '#222222',
     '#E41A1C',
     '#377EB8',
     '#4DAF4A',
     '#984EA3',
     '#FF7F00',
     ]
    rc('font', size='8')
    rc('font', family='serif')
    for capname in capdirs:
        fig = plt.figure(figsize=(4,2))
        ax1 = fig.add_subplot(111)
        
        colors = iter(H)
        markers = iter(['s', 'p', 'o', 'v', '^', 'h'])
        
        legend_lines = []
        legend_names = []
        for algo_priority_name in individual_wanted:
            
            motionpath_data = algo_rawdata[algo_priority_name]
            
            legend_names.append(algo_priority_name)
            algo_trials = motionpath_data[capname]
            color = next(colors)
            marker = next(markers)
            for i, trial in enumerate(algo_trials):
                errvals = (numpy.array(trial['errvals'], dtype=float) / (1024 * 768)) * 100
                res = ax1.plot(trial['times'], errvals, color=color, marker=marker, markersize=2, linewidth=0.5, markeredgewidth=0.2)
                if i == 0:
                    legend_lines.append(res)
                    break
        
        prop = FontProperties(size=5)
        l1, l2, l3, l4, l5, l6 = legend_lines
        leg = plt.legend(l1+l2+l3+l4+l5+l6, legend_names, loc='upper right', prop=prop, ncol=4, frameon=False, columnspacing=0.5)
        
        # swap_and_right_align_legend
        for vp in leg._legend_box._children[-1]._children:
            for c in vp._children:
                c._children.reverse()
            vp.align = "right"
        
        dangling1 = leg._legend_box._children[-1]._children[0]._children.pop(0)
        dangling2 = leg._legend_box._children[-1]._children[1]._children.pop(0)
        leg._legend_box._children[-1]._children[2]._children.append(dangling1)
        leg._legend_box._children[-1]._children[3]._children.append(dangling2)
        
        #plt.title('Error Over Time (%s)' % capname[8:-5])
        plt.xlabel('Time (s)')
        plt.ylabel('Perceptual Error (\% screen size)')
        plt.yticks(range(0, 109, 10))
        plt.ylim((0, 113))
        ax1.xaxis.set_ticks_position('bottom')
        ax1.yaxis.set_ticks_position('left')
        plt.subplots_adjust(left=0.12, right=0.97, top=0.95, bottom=0.15)
        plt.savefig(os.path.join(graphdir, 'rawcaps-' + capname + '.pdf'))
    
    positions = numpy.arange(len(algo_results)) + 0.2
    names = []
    percentages = []
    for mean, name in sorted(algo_results):
        names.append(name)
        percentages.append((mean / (1024 * 768)) * 100)
    
    fig = plt.figure(figsize=(4, 2.5))
    ax1 = fig.add_subplot(111)
    
    H = ['#FBB4AE',
     '#B3CDE3',
     '#CCEBC5',
     '#DECBE4',
     '#FED9A6',
     '#ff0000']
    H1, H2, H3, H4, H5, H6 = H
    W = '#ffffff'
    colors = [H1, H5, H1, H3, H2, W, H5, H3, H3, H3, W, H1, H1, H3, H3, H3]
    colors = [H1, W, H2, H3, W, H1, H3, H2, H2, H2, W, H1, H2, H1, H2, H2]
    
    rc('font', size='10')
    rc('font', family='serif')
    textprop1 = FontProperties(size=5)
    textprop2 = FontProperties(size=7)
    rects = ax1.bar(positions, percentages, color=colors)
    
    def autolabel(rects, labels):
        maxheight = max(rect.get_height() for rect in rects)
        for i, (rect, label) in enumerate(zip(rects, labels)):
            height = rect.get_height()
            yloc = height + maxheight * 0.03
            if i > 7:
                yloc = 1
            plt.text(rect.get_x() + rect.get_width() / 2.0, yloc, label,
                    ha='center', va='bottom', rotation=90, fontproperties=textprop2)
            plt.text(rect.get_x() + rect.get_width() / 2.0, height - maxheight * 0.04, '%0.1f' % rect.get_height(),
                    ha='center', va='bottom', clip_on=True, fontproperties=textprop1)
    
    autolabel(rects, names)
    
    #ax1.get_xaxis().set_visible(False)
    ax1.yaxis.set_ticks_position('left')
    plt.yticks(range(0, 101, 10))
    plt.xticks(positions+0.4, [chr(i+65) for i in range(len(positions))])
    for t in ax1.xaxis.get_ticklines():
        t.set_visible(False)
    plt.ylabel('Mean Perceptual Error')
    plt.xlim((0, max(positions)+rects[0].get_width()+0.2))
    plt.ylim((0, max(percentages)+1))
    #plt.title('Perceptual Error by Priority Algorithm')
    plt.subplots_adjust(left=0.14, right=0.98, top=0.97, bottom=0.11)
    plt.savefig(os.path.join(graphdir, 'algo-percentages-bar.pdf'))
    
    
    rc('font', size='18')
    rc('font', family='sans-serif')
    fig = plt.figure(figsize=(11.5, 8))
    ax1 = fig.add_subplot(111)
    
    positions = numpy.arange(len(algo_results)) + 0.1
    bar_width = 0.1
    algo_order = [name for mean, name in sorted(algo_results)]
    colors = iter(['b', 'r', 'g', 'k', 'y', 'b', 'r', 'g'])
    
    cap_means = {}
    cap_percentages = {}
    cap_mins = {}
    cap_maxes = {}
    for capname in capdirs:
        percentages = []
        mins = []
        maxes = []
        for algo_name in algo_order:
            meanval = (numpy.mean(algo_motion_means[algo_name][capname]) / (1024 * 768)) * 100
            percentages.append(meanval)
            minval = (numpy.min(algo_motion_means[algo_name][capname]) / (1024 * 768)) * 100
            mins.append(meanval - minval)
            maxval = (numpy.max(algo_motion_means[algo_name][capname]) / (1024 * 768)) * 100
            maxes.append(maxval - meanval)
        
        cap_mins[capname] = mins
        cap_maxes[capname] = maxes
        cap_percentages[capname] = percentages
        cap_means[capname] = numpy.mean(percentages)
    
    caps_sorted = sorted((capname, mean) for mean, capname in cap_means.iteritems())
    caporder = [capname for mean, capname in caps_sorted]
    
    rects = []
    for i, capname in enumerate(caporder):
        errvals = ((cap_mins[capname], cap_maxes[capname]))
        rect = ax1.bar(positions + bar_width*i,
                        cap_percentages[capname],
                        bar_width,
                        yerr=errvals,
                        color=next(colors))
        rects.append(rect)
    
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
