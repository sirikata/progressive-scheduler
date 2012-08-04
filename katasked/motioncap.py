import panda3d.core as p3d
import panda3d.egg as egg
import direct.directutil.Mopath as Mopath
import direct.showbase.PythonUtil as directutil

class CreateNurbsCurve(object):
    def __init__(self):
        self.data = egg.EggData()
        self.vtxPool = egg.EggVertexPool('mopath')
        self.data.addChild(self.vtxPool)
        self.eggGroup = egg.EggGroup('group')
        self.data.addChild(self.eggGroup)
        self.myverts = []
        self.myrotverts = []
        self.finished = False
        self.order = 3
    
    def addPoint(self, pos, hpr=None):
        if hpr:
            eggVtx = egg.EggVertex()
            
            if len(self.myrotverts) > 0:
                prev = self.myrotverts[-1].getPos3()
                hpr = [directutil.fitDestAngle2Src(old, new)
                       for old,new in zip(prev, hpr)]
            
            eggVtx.setPos(p3d.Point3D(hpr[0], hpr[1], hpr[2]))
            self.myrotverts.append(eggVtx)
            self.vtxPool.addVertex(eggVtx)
        if self.myrotverts and not hpr:
            print "you started to add rotations.. you better see it through now!"
        
        eggVtx = egg.EggVertex()
        eggVtx.setPos(p3d.Point3D(pos[0], pos[1], pos[2]))
        self.myverts.append(eggVtx)
        self.vtxPool.addVertex(eggVtx)

    def getEggData(self):
        if not self.finished:
            myCurve = egg.EggNurbsCurve()
            myCurve.setup(self.order, len(self.myverts) + self.order)
            myCurve.setCurveType(1)
            for i in self.myverts:
                myCurve.addVertex(i)
            self.eggGroup.addChild(myCurve)
            
            if self.myrotverts:
                myCurve = egg.EggNurbsCurve()
                myCurve.setup(self.order, len(self.myverts) + self.order)
                myCurve.setCurveType(2)
                for i in self.myrotverts:
                    myCurve.addVertex(i)
                self.eggGroup.addChild(myCurve)
            
            self.finished = True
        
        return self.data

    def getNodePath(self):
        return p3d.NodePath(egg.loadEggData(self.getEggData()))
    
    def getMotionPath(self):
        np = self.getNodePath()
        mopath = Mopath.Mopath()
        mopath.loadNodePath(np)
        mopath.fFaceForward = True
        return mopath
    