#!/usr/bin/env python2

import os
import json
import subprocess

import argparse
import clint.textui.progress as progress

import pathmangle
import katasked.util as util

def main():
    parser = argparse.ArgumentParser(description='Compares screenshots from loadscene and fullscene_screenshotter using perceptualdiff')
    parser.add_argument('--screenshot-dir', '-d', metavar='directory', required=True, action='append',
                        help='Directory where screenshots were dumped and data will be saved')
    
    args = parser.parse_args()

    perceptualdiff = util.which("perceptualdiff")
    if perceptualdiff is None:
        parser.error("perceptualdiff binary not found on path")

    for d in args.screenshot_dir:
        d = os.path.abspath(d)
        
        realtime_files = sorted(os.listdir(os.path.join(d, 'realtime')))
        groundtruth_files = sorted(os.listdir(os.path.join(d, 'groundtruth')))
        
        assert len(realtime_files) == len(groundtruth_files)
        
        file_errors = []
        
        for realtime_file, groundtruth_file in progress.bar(zip(realtime_files, groundtruth_files), label='Processing directory %s...' % d):
            realtime_file = os.path.join(d, 'realtime', realtime_file)
            groundtruth_file = os.path.join(d, 'groundtruth', groundtruth_file)
            
            try:
                output = subprocess.check_output([perceptualdiff, '-threshold', '1', realtime_file, groundtruth_file], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError, e:
                output = e.output
            
            output = output.strip()
            if len(output) == 0:
                pixels = 0
            else:
                lines = output.split("\n")
                pixels = int(lines[1].split()[0])
            
            file_errors.append({'filename': os.path.basename(realtime_file),
                                'perceptualdiff': pixels})
        
        with open(os.path.join(d, 'perceptualdiff.json'), 'w') as f:
            json.dump(file_errors, f, indent=2)

if __name__ == '__main__':
    main()
