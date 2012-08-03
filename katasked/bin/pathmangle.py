import os
import sys

try:
    import katasked
except ImportError:
    # adds katasked dir to path
    CURDIR = os.path.dirname(os.path.abspath(__file__)) # repodir/katasked/bin
    KATASKED_DIR = os.path.split(CURDIR)[0] # repodir/katasked
    ROOT_DIR = os.path.split(KATASKED_DIR)[0] # repodir
    sys.path.append(ROOT_DIR)
