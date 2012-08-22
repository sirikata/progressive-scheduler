import os

try:
    from cython_impl import *
except ImportError:
    CURDIR = os.path.dirname(os.path.abspath(__file__))
    print ('Warning: using unoptimized python version of katasked.task.priority. '
           'Run "python setup.py build_ext --inplace" from directory '
           '"%s" to use optimized version.' % CURDIR)
    from python_impl import *
