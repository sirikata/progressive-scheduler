#!/usr/bin/env python2

import os
import json
import time
import subprocess

import argparse
import clint.textui.progress as progress

import pathmangle
import katasked.util as util

WINDOW_SIZE = 6

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
        
        info_fname = os.path.join(d, 'info.json')
        with open(info_fname, 'r') as f:
            ss_info = json.load(f)
        
        filenames = [ss['filename'] for ss in ss_info]
        file_errors = []
        
        tocompare = []
        for fname in filenames:
            realtime_file = os.path.join(d, 'realtime', fname)
            groundtruth_file = os.path.join(d, 'groundtruth', fname)
            
            tocompare.append((realtime_file, groundtruth_file))
        
        running = []
        while len(running) > 0 or len(tocompare) > 0:
            while len(running) < WINDOW_SIZE and len(tocompare) > 0:
                realtime_file, groundtruth_file = tocompare.pop()
                print '=====>', realtime_file
                p = subprocess.Popen([perceptualdiff, '-threshold', '1', realtime_file, groundtruth_file],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                running.append((realtime_file, p))
            
            new_running = []
            finished = []
            for realtime_file, p in running:
                if p.poll() is None:
                    new_running.append((realtime_file, p))
                else:
                    finished.append((realtime_file, p))
            running = new_running
            
            for realtime_file, p in finished:
                output = p.stdout.read()
                output = output.strip()
                
                if len(output) == 0:
                    pixels = 0
                else:
                    lines = output.split("\n")
                    pixels = int(lines[1].split()[0])
                
                print '<==(%d)==' % pixels, realtime_file
                
                file_errors.append({'filename': os.path.basename(realtime_file),
                                    'perceptualdiff': pixels})
            
            time.sleep(0.2)
        
        file_errors.sort(key=lambda i: float('.'.join(i['filename'].split('.')[:2])))
        
        with open(os.path.join(d, 'perceptualdiff.json'), 'w') as f:
            json.dump(file_errors, f, indent=2)

if __name__ == '__main__':
    main()
