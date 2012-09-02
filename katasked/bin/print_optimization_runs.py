#!/usr/bin/env python2

import os
import sys
import json
import collections

import argparse

def main():
    parser = argparse.ArgumentParser(description='Prints the output of an optimization run in a table format')
    parser.add_argument('--experiment-dir', '-d', metavar='directory', required=True,
                        help='Directory where experiment was output to')
    
    args = parser.parse_args()
    
    expdir = os.path.abspath(args.experiment_dir)
    if os.path.exists(expdir) and not os.path.isdir(expdir):
        parser.error('Invalid directory: %s' % expdir)
    
    dirs = sorted(os.listdir(expdir))
    dirvalues = collections.OrderedDict()
    inputvars = None
    for d in dirs:
        datafile = os.path.join(expdir, d, 'iteration.json')
        if not os.path.exists(datafile):
            continue
        iterdata = json.loads(open(datafile, 'r').read())
        inputset = set(iterdata['inputs'].keys())
        if inputvars is None:
            inputvars = inputset
        else:
            inputvars = inputvars.intersection(inputset)
        dirvalues[int(d)] = iterdata
    
    labels = ['iternum'] + list(inputvars) + ['mean_err']
    MINW = 10
    min_mean = sys.maxint
    min_iternum = -1
    print '  '.join(label.rjust(max(len(label),MINW)) for label in labels)
    print '  '.join('=' * max(len(label),MINW) for label in labels)
    for iternum, iterdata in dirvalues.iteritems():
        sys.stdout.write(('%d' % iternum).rjust(max(len('iternum'),MINW)))
        sys.stdout.write('  ')
        for label in labels[1:-1]:
            sys.stdout.write(('%0.2f' % iterdata['inputs'][label]).rjust(max(len(label),MINW)))
            sys.stdout.write('  ')
        sys.stdout.write(('%0.2f' % iterdata['mean']).rjust(max(len('mean_err'),MINW)))
        sys.stdout.write('  \n')
        if iterdata['mean'] < min_mean:
            min_mean = iterdata['mean']
            min_iternum = iternum
    
    print
    print 'Minimum mean error %.2f at iteration #%d' % (min_mean, min_iternum)
    print

if __name__ == '__main__':
    main()
