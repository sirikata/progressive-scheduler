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

* bin/pathcapture.py - captures a motion path for a scene into a JSON file
* bin/pathreplay.py - replays a motion path for a scene
