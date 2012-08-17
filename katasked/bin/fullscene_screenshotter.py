#!/usr/bin/env python2

import os
import json

import argparse
from clint.textui import progress

import pathmangle
import katasked.loader as loader
import katasked.cache as cache
import katasked.task.priority as priority
import katasked.open3dhub as open3dhub

class FullSceneScreenshotLoader(loader.ProgressiveLoader):
    def __init__(self, scenefile, screenshot_dirs):
        loader.ProgressiveLoader.__init__(self, scenefile)
        
        
        self.all_cached = all(cache.is_bam_cached(modelslug + "_full.bam") for modelslug in self.unique_nodepaths.keys())
        if self.all_cached:
            for modelslug, np in progress.bar(self.unique_nodepaths.items(), label='Loading cached full resolution models...'):
                key = modelslug + "_full.bam"
                modelpath = self.loader.loadModel(cache.get_bam_file(key))
                geomnode = modelpath.getChild(0)
                
                self.unique_nodepaths[modelslug] = geomnode
                
                if self.instance_count[modelslug] == 1:
                    geomnode.reparentTo(np)
                else:
                    for instance_np in self.nodepaths_byslug[modelslug]:
                        geomnode.instanceTo(instance_np)
                    self.rigid_body_combiners[modelslug].collect()
        
        self.dumpdirs = screenshot_dirs
        
        self.camera_points = []
        for dumpdir in self.dumpdirs:
            info_file = os.path.join(dumpdir, 'info.json')
            with open(info_file, 'r') as f:
                self.camera_points.append(json.load(f))
    
    def run(self):
        if self.all_cached:
            self.taskMgr.remove(self.update_camera_predictor_task)
            self.taskMgr.remove(self.update_priority_task)
            self.taskMgr.remove(self.load_waiting_task)
        
        else:
            self.render.hide()
            while self.multiplexer.empty() != True or len(self.waiting) > 0:
                self.taskMgr.step()
                self.taskMgr.step()
            
            self.render.show()
            
            for modelslug, np in self.unique_nodepaths.iteritems():
                key = "%s_full.bam" % modelslug
                print 'adding full cache', key
                cache.add_bam(key, np)
        
        for dumpdir, camera_points in zip(self.dumpdirs, self.camera_points):
            print 'Dumping screenshots for directory %s...' % dumpdir
            for camera_pt in camera_points:
                fname = camera_pt['filename']
                position = camera_pt['position']
                hpr = camera_pt['hpr']
                self.cam.setPosHpr(*(position + hpr))
                
                self.taskMgr.step()
                self.taskMgr.step()
                
                self.win.saveScreenshot(os.path.join(dumpdir, 'groundtruth', fname))

def main():
    parser = argparse.ArgumentParser(description='Fully loads a scene and then captures screenshots based on a previous run of loadscene.py')
    parser.add_argument('--scene', '-s', metavar='scene.json', type=argparse.FileType('r'), required=True,
                        help='Scene file to render.')
    parser.add_argument('--screenshot-dir', '-d', metavar='directory', default=list(), action='append',
                        help='Directory where screenshots were dumped and will be dumped')
    parser.add_argument('--cache-dir', metavar='directory', help='Directory to use for cache files')
    parser.add_argument('--priority-algorithm', choices=priority.get_priority_algorithm_names(),
                        help='The algorithm used for prioritizing tasks')
    parser.add_argument('--cdn-domain', metavar='example.com')
    
    args = parser.parse_args()

    screenshot_dirs = []
    for outdir in args.screenshot_dir:
        outdir = os.path.abspath(outdir)
        screenshot_dirs.append(outdir)
        if os.path.exists(outdir) and not os.path.isdir(outdir):
            parser.error('Invalid screenshots directory: %s' % outdir)
        elif not os.path.exists(os.path.join(outdir, 'groundtruth')):
            os.makedirs(os.path.join(outdir, 'groundtruth'))
    
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
    
    if args.cdn_domain is not None:
        open3dhub.set_cdn_domain(args.cdn_domain)
    
    app = FullSceneScreenshotLoader(args.scene, screenshot_dirs)
    app.run()

if __name__ == '__main__':
    main()
