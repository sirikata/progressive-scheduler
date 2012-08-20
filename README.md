# progressive-scheduler

A an evaluation framework for progressive mesh scheduling

## Installation

 * [Panda3D](http://www.panda3d.org/) is required. Mac and Windows users
   should download and install the
   [latest SDK](http://www.panda3d.org/download.php?sdk). On Ubuntu, create
   ``/etc/apt/sources.list.d/panda3d.list`` with the contents
   ``deb http://archive.panda3d.org/ubuntu precise main`` and you can install
   Panda3D using apt-get. Just replace precise with your release name.

 * The rest of the requirements can be installed via pip with the following
   command: ``pip install -r requirements.txt``.

## Scripts

### Motion Capture

* bin/pathcapture.py - captures a motion path for a scene into a JSON file
* bin/pathreplay.py - replays a motion path for a scene

### Scene Loading

* bin/loadscene.py - loads a scene progressively, with an optional motion path
* bin/fullscene_screenshotter.py - loads a scene completely and then takes
  screenshots

### Experiment Scripts

* bin/perceptual_differ.py - compare loadscene.py screenshots with
  fullscene_screenshotter.py screenshots using perceptualdiff
* bin/priority_experiment_runner.py - runs cycles of loadscene,
  fullscene_screenshotter, and perceptual_differ for each priority algorithm
* bin/optimization_runner.py - runs cycles of loadscene, fullscene_screenshotter,
  and perceptual_differ, changing the priority weights using FromFile method
  based on the inputs from scipy.optimize.minimize algorithm

### Graphing

* bin/priority_experiment_graph.py - graphs the result of priority_experiment_runner.py
