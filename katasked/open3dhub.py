import json
import posixpath
from StringIO import StringIO
import os
import requests
import urlparse

import collada
from meshtool.filters.panda_filters import pandacore
from meshtool.filters.panda_filters import pdae_utils
from meshtool.filters.simplify_filters import add_back_pm
from meshtool.filters.print_filters.print_bounds import getBoundsInfo
import panda3d.core as p3d

import cache
import panda
import util

BASE_DOMAIN = None
BASE_URL = None
BROWSE_URL = None
DOWNLOAD_URL = None
DNS_URL = None
MODELINFO_URL = None
SEARCH_URL = None

PANDA3D = False

PROGRESSIVE_CHUNK_SIZE = 2 * 1024 * 1024 # 2 MB

CURDIR = os.path.dirname(__file__)
TEMPDIR = os.path.join(CURDIR, '.temp_models')

def _get_session():
    return requests.session(timeout=6)
REQUESTS_SESSION = _get_session()

def set_cdn_domain(domain):
    global BASE_DOMAIN, BASE_URL, BROWSE_URL, DOWNLOAD_URL, \
            DNS_URL, MODELINFO_URL, SEARCH_URL

    BASE_DOMAIN = domain
    BASE_URL = 'http://%s' % BASE_DOMAIN
    BROWSE_URL = BASE_URL + '/api/browse'
    DOWNLOAD_URL = BASE_URL + '/download'
    DNS_URL = BASE_URL + '/dns'
    MODELINFO_URL = BASE_URL + '/api/modelinfo/%(path)s'
    SEARCH_URL = BASE_URL + '/api/search?q=%(q)s&start=%(start)d&rows=%(rows)d'

set_cdn_domain('open3dhub.com')

class PathInfo(object):
    """Helper class for dealing with CDN paths"""
    def __init__(self, filename):
        self.filename = filename
        self.normpath = posixpath.normpath(filename)
        """Normalized original path"""
        
        split = self.normpath.split("/")
        try:
            self.version = str(int(split[-1]))
            """Version number of the path"""
        except ValueError:
            self.version = None
    
        if self.version is None:
            self.basename = split[-1]
            """The filename of the path"""
            self.basepath = self.normpath
            """The base of the path, without the version number"""
        else:
            self.basename = split[-2]
            self.basepath = '/'.join(split[:-1])
            
    @staticmethod
    def fromurl(url):
        parsed = urlparse.urlparse(url)
        return PathInfo(parsed.path)
            
    def __str__(self):
        return "<PathInfo filename='%s', normpath='%s', basepath='%s', basename='%s', version='%s'>" % \
                (self.filename, self.normpath, self.basepath, self.basename, self.version)
    
    def __repr__(self):
        return str(self)

# this will retry 4 times with exponential backoff: 1 second, 2, 4, 8
@util.retry((requests.HTTPError, requests.Timeout, requests.ConnectionError), 4, 1, 2)
def urlfetch(url, httprange=None):
    """Fetches the given URL and returns data from it.
    Will take care of gzip if enabled on server."""
    global REQUESTS_SESSION
    
    headers = {}
    if httprange is not None:
        offset, length = httprange
        headers['Range'] = 'bytes=%d-%d' % (offset, offset+length-1)
    
    try:
        resp = REQUESTS_SESSION.get(url, headers=headers)
        # raises HTTPError on non-200 response
        resp.raise_for_status()
    except (requests.HTTPError, requests.Timeout, requests.ConnectionError):
        # close all open connections if we get some error
        REQUESTS_SESSION.close()
        REQUESTS_SESSION = _get_session()
        # then re-raise so it will retry
        raise
    
    return resp.content
    
def json_fetch(url):
    try:
        return json.loads(urlfetch(url))
    except ValueError:
        print 'Error receiving json for url', url
        raise

def hashfetch(dlhash, httprange=None):
    key = 'HASH_' + dlhash
    url = DOWNLOAD_URL + '/' + dlhash
    if httprange is not None:
        offset, length = httprange
        key += "_%d_%d" % (offset, length)
        url += "?start=%d&end=%d" % (offset, offset+length-1)
    data = cache.cache_data_wrap(key, urlfetch, url)
    if httprange is not None and len(data) != length:
        print 'GOT INCORRECT LENGTH', key, dlhash, httprange, len(data)
        assert len(data) == length
    return data

def get_subfile_hash(subfile_path):
    subfile_url = DNS_URL + subfile_path
    subfile_json = json.loads(urlfetch(subfile_url))
    subfile_hash = subfile_json['Hash']
    return subfile_hash

def get_search_list(q):
    start = 0
    
    all_items = []
    while start is not None:
        to_search = SEARCH_URL % {'q': q,
                                  'start': start,
                                  'rows': 100}
        response = json_fetch(to_search)
        
        all_items.extend(response['content_items'])
        
        try:
            start = int(response['next_start'])
        except (ValueError, TypeError):
            start = None
    
    return all_items

def get_metadata(path):
    pathinfo = PathInfo(path)
    return cache.cache_metadata_wrap('METADATA_' + str(path), json_fetch, MODELINFO_URL % {'path': pathinfo.normpath})

def get_tag(tag):
    return cache.cache_metadata_wrap('TAG_' + tag, get_search_list, 'tags:"%s"' % tag)

def _make_aux_file_loader(metadata):

    typedata = metadata['metadata']['types']['optimized']
    subfile_map = {}
    for subfile in typedata['subfiles']:
        base_name = posixpath.basename(posixpath.split(subfile)[0])
        subfile_map[base_name] = subfile

    def aux_file_loader(fname):
        base = posixpath.basename(fname)
        if base not in subfile_map:
            return None
        path = subfile_map[base]
        subhash = get_subfile_hash(path)
        data = hashfetch(subhash)
        return data

    return aux_file_loader

def path_to_mesh(path):
    metadata = get_metadata(path)
    typedata = metadata['metadata']['types']['optimized']
    mesh_hash = typedata['hash']
    mesh_data = hashfetch(mesh_hash)
    mesh = collada.Collada(StringIO(mesh_data), aux_file_loader=_make_aux_file_loader(metadata))
    return mesh

def load_mesh(mesh_data, subfiles):
    """Given a downloaded mesh, return a collada instance"""
    
    def inline_loader(filename):
        return subfiles[posixpath.basename(filename)]
    
    mesh = collada.Collada(StringIO(mesh_data), aux_file_loader=inline_loader)
    
    #this will force loading of the textures too
    for img in mesh.images:
        img.data
    
    return mesh

def texture_data_to_nodepath(texture_data):
    tex = pandacore.textureFromData(texture_data)
    tex.generateSimpleRamImage()
    np = p3d.NodePath(p3d.PandaNode("dummytexture"))
    np.setTexture(tex)
    return np

def _load_into_bamfile(bam_file, meshdata, boundsInfo, subfiles, model_name):
    if meshdata is None:
        try:
            np = texture_data_to_nodepath(subfiles)
        except:
            print 'ERROR', bam_file, model_name
            raise
    else:
        mesh = load_mesh(meshdata, subfiles)
        np = panda.mesh_to_nodepath(mesh, boundsInfo)
    np.setName(model_name)
    np.writeBamFile(bam_file)

def load_into_bamfile(meshdata, boundsInfo, subfiles, modelslug):
    """Uses pycollada and panda3d to load meshdata and subfiles and write out to a bam file on disk"""
    return cache.cache_bam_wrap(modelslug + '.bam', meshdata, boundsInfo, subfiles, modelslug)

