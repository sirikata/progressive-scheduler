#!/usr/bin/env python2

import os

import argparse

import pathmangle
import katasked.loader as loader
import katasked.cache as cache
import katasked.task.priority as priority

def main():
    parser = argparse.ArgumentParser(description='Progressively loads a scene')
    parser.add_argument('--capture', '-c', metavar='motioncap.json', type=argparse.FileType('r'),
                        help='File of the motion capture to use for the camera. If not specified, keyboard and mouse controls are enabled.')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
    parser.add_argument('--show-stats', action='store_true', default=False,
                        help='Display on-screen statistics about scene while loading')
    parser.add_argument('--dump-screenshot', '-d', metavar='directory', help='Directory to dump screenshots to')
    parser.add_argument('--cache-dir', metavar='directory', help='Directory to use for cache files')
    parser.add_argument('--priority-algorithm', choices=priority.get_priority_algorithm_names(),
                        help='The algorithm used for prioritizing tasks')
    
    args = parser.parse_args()
    
    outdir = None
    if args.dump_screenshot is not None:
        outdir = os.path.abspath(args.dump_screenshot)
        if os.path.exists(outdir) and not os.path.isdir(outdir):
            parser.error('Invalid screenshots directory: %s' % outdir)
        elif not os.path.exists(os.path.join(outdir, 'realtime')):
            os.makedirs(os.path.join(outdir, 'realtime'))
    
    cachedir = None
    if args.cache_dir is not None:
        cachedir = os.path.abspath(args.cache_dir)
        if os.path.exists(cachedir) and not os.path.isdir(cachedir):
            parser.error('Invalid cache directory: %s' % cachedir)
        elif not os.path.exists(cachedir):
            os.mkdir(cachedir)
    
    cache.init_cache(cachedir)
    
    if args.priority_algorithm is not None:
        algorithm = priority.get_algorithm_by_name(args.priority_algorithm)
        priority.set_priority_algorithm(algorithm())
    
    app = loader.ProgressiveLoader(args.scene,
                                   capturefile=args.capture,
                                   showstats=args.show_stats,
                                   screenshot_dir=outdir)
    app.run()

if __name__ == '__main__':
    main()
