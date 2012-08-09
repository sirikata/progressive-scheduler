import panda3d.core as p3d
import meshtool.filters.panda_filters.pdae_utils as pdae_utils

def update_nodepath(pandaNode, refinements):
    geom = pandaNode.modifyGeom(0)
    
    vertdata = geom.modifyVertexData()
    prim = geom.modifyPrimitive(0)
    indexdata = prim.modifyVertices()
    
    indexwriter = p3d.GeomVertexWriter(indexdata)
    indexwriter.setColumn(0)
    nextTriangleIndex = indexdata.getNumRows()
    
    vertwriter = p3d.GeomVertexWriter(vertdata, 'vertex')
    numverts = vertdata.getNumRows()
    vertwriter.setRow(numverts)
    normalwriter = p3d.GeomVertexWriter(vertdata, 'normal')
    normalwriter.setRow(numverts)
    uvwriter = p3d.GeomVertexWriter(vertdata, 'texcoord')
    uvwriter.setRow(numverts)
    
    for refinement in refinements:
        for op_index in range(len(refinement)):
            vals = refinement[op_index]
            op = vals[0]
            if op == pdae_utils.PM_OP.TRIANGLE_ADDITION:
                indexwriter.setRow(nextTriangleIndex)
                nextTriangleIndex += 3
                indexwriter.addData1i(vals[1])
                indexwriter.addData1i(vals[2])
                indexwriter.addData1i(vals[3])
            elif op == pdae_utils.PM_OP.INDEX_UPDATE:
                indexwriter.setRow(vals[1])
                indexwriter.setData1i(vals[2])
            elif op == pdae_utils.PM_OP.VERTEX_ADDITION:
                numverts += 1
                vertwriter.addData3f(vals[1], vals[2], vals[3])
                normalwriter.addData3f(vals[4], vals[5], vals[6])
                uvwriter.addData2f(vals[7], vals[8])
