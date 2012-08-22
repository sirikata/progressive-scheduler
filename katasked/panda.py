import numpy
import collada
import panda3d.core as p3d
import meshtool.filters.panda_filters.pandacore as pcore

class PandaState(object):
    def __init__(self, camera, unique_nodepaths, nodepaths, camera_smoother, globalClock, obj_bounds):
        self.camera = camera
        """Panda3D camera"""
        self.unique_nodepaths = unique_nodepaths
        """A dict mapping SceneModel.slug to its unique NodePath in scene"""
        self.nodepaths = nodepaths
        """A dict mapping SceneModel to its NodePath instances in scene"""
        self.camera_smoother = camera_smoother
        """An instance of SmoothMover that can be used to predict camera"""
        self.globalClock = globalClock
        """The Panda3D global clock"""
        self.obj_bounds = obj_bounds
        """Sphere bounding boxes for each nodepath"""

def centerAndScale(nodePath, boundsInfo):

    parentNP = nodePath.getParent()
    
    nodePath.detachNode()
    nodePath.setName('wrapper-centering-collada')
    
    newRoot = parentNP.attachNewNode('newroot')
    
    scaleNode = newRoot.attachNewNode('scaler')
    nodePath.reparentTo(scaleNode)

    center = boundsInfo['center']
    center_distance = boundsInfo['center_farthest_distance']

    nodePath.setPos(-1 * center[0],
                    -1 * center[1],
                    -1 * center[2])

    scale = 1.0 / center_distance
    scaleNode.setScale(scale, scale, scale)
    
    return newRoot

def mesh_to_nodepath(mesh, boundsInfo):
    scene_members = pcore.getSceneMembers(mesh)
    
    rootNode = p3d.NodePath("rootnode")
    rotatePath = rootNode.attachNewNode("rotater")
    matrix = numpy.identity(4)
    if mesh.assetInfo.upaxis == collada.asset.UP_AXIS.X_UP:
        r = collada.scene.RotateTransform(0,1,0,90)
        matrix = r.matrix
    elif mesh.assetInfo.upaxis == collada.asset.UP_AXIS.Y_UP:
        r = collada.scene.RotateTransform(1,0,0,90)
        matrix = r.matrix
    rotatePath.setMat(p3d.Mat4(*matrix.T.flatten().tolist()))
    
    modelNode = p3d.ModelNode("colladanode")
    modelNode.setPreserveTransform(p3d.ModelNode.PTNet)
    modelPath = rotatePath.attachNewNode(modelNode)
    for geom, renderstate, mat4 in scene_members:
        node = p3d.GeomNode("primitive")
        node.addGeom(geom)
        if renderstate is not None:
            # FIXME: disabled transparency attrib because of progressive transparency bug
            renderstate = renderstate.removeAttrib(p3d.ColorScaleAttrib)
            node.setGeomState(0, renderstate)
        geomPath = modelPath.attachNewNode(node)
        geomPath.setMat(mat4)
    
    newroot = centerAndScale(rotatePath, boundsInfo)
    newroot.flattenStrong()
    return modelPath
