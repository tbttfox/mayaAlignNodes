from __future__ import print_function
from maya import OpenMayaUI as mui, OpenMaya as om, cmds
from PySide2.QtWidgets import (
    QGraphicsItem,
    QWidget,
    QGraphicsView,
    QStackedLayout,
    QGraphicsSimpleTextItem,
)

from contextlib import contextmanager
from shiboken2 import wrapInstance
import sys
import copy

if sys.version_info.major == 3:
    long = int


@contextmanager
def restoreSel():
    """ Restore the current selection
    Make sure to turn off undo so that the quick selects
    don't pollute the queue
    """
    store = cmds.ls(sl=True, long=True)
    cmds.undoInfo(state=False)
    try:
        yield
    finally:
        cmds.select(store)
        cmds.undoInfo(state=True)


class xSetter(object):
    """ A class that handles getting/setting the X values
    of a group of objects with a consistent interface
    """

    @staticmethod
    def set(item, val):
        item.setX(val)

    @staticmethod
    def getItemPos(items):
        return [i.pos().x() for i in items]

    @staticmethod
    def getSizes(items):
        return [i.sceneBoundingRect().width() for i in items]


class ySetter(object):
    """ A class that handles getting/setting the Y values
    of a group of objects with a consistent interface
    """

    @staticmethod
    def set(item, val):
        item.setY(val)

    @staticmethod
    def getItemPos(items):
        return [i.pos().y() for i in items]

    @staticmethod
    def getSizes(items):
        return [i.sceneBoundingRect().height() for i in items]


class NodeEditorUI(object):
    def __init__(self):
        self._graphView = None
        self._scene = None
        self._name = None

    def _getCurrentView(self):
        pan = cmds.getPanel(scriptType="nodeEditorPanel")[0]
        self._name = pan + "NodeEditorEd"
        ctrl = mui.MQtUtil.findControl(self._name)
        if ctrl is None:
            raise RuntimeError("Node editor is not open")
        nodeEdPane = wrapInstance(long(ctrl), QWidget)
        stack = nodeEdPane.findChild(QStackedLayout)
        self._graphView = stack.currentWidget().findChild(QGraphicsView)
        self._scene = self._graphView.scene()

    @property
    def graphView(self):
        if self._graphView is None:
            self._getCurrentView()
        return self._graphView

    @property
    def scene(self):
        if self._scene is None:
            self._getCurrentView()
        return self._scene

    @property
    def name(self):
        if self._name is None:
            self._getCurrentView()
        return self._name

    def getSelItems(self):
        """ Get the nodes selected in the UI panel

        Returns:
            list(QGraphicsItem): The selected items in the current editor tab
        """
        items = self.scene.selectedItems()
        # There are also
        # QGraphicsPathItems (The connection lines)
        # QGraphicsSimpleTextItem (The node names)
        # QGraphicsWidget (The sub-sections of each node, like the tree and filter lines)
        items = [i for i in items if type(i) is QGraphicsItem]
        return items

    def getAllItems(self):
        """ Get all nodes in the UI panel

        Returns:
            list(QGraphicsItem): The nodes in the current editor tab
        """
        items = self.scene.items()
        items = [i for i in items if type(i) is QGraphicsItem]
        return items

    @staticmethod
    def getNodeName(self, node):
        """ Get the short name of the passed QGraphicsItem

        Currently, I don't know of a way to get the full path to the item
        because there's no direct link from GraphicsNode to MObject

        Arguments:
            node (QGraphicsItem): The node to get the name of

        Returns:
            str: The name of the passed node
        """
        # TODO: Try and get the full node name
        chis = node.childItems()
        chis = [i for i in chis if isinstance(i, QGraphicsSimpleTextItem)]
        if not chis:
            return None
        nameItem = chis[0]
        return ':'.join(nameItem.text().split())

    @staticmethod
    def getItemPos(items):
        """ Get the x/y positions of the given UI items in the node editor """
        nodePosList = []
        for i in items:
            nodePosList.append([i.pos().x(), i.pos().y()])
        return nodePosList

    @staticmethod
    def align(items, setter, prc=0.0):
        """ A funciton that aligns the center lines of a group of items
        along an axis determined by the given setter

        Arguments:
            items (list): The QGraphicsItems to align
            setter (Setter): The setter class
            prc (float): The percentage between the min/max value to align
                A zero value aligns to the topmost node
        """
        ipos = setter.getItemPos(items)
        sizes = setter.getSizes(items)
        minX = min(ipos)
        off = prc * sizes[0]
        for j, s in zip(items, sizes):
            setter.set(j, minX - (prc * s) + off)

    @staticmethod
    def spread(items, setter, offset=5.0):
        """
        A funciton that evenly spreads the given items along an axis
        determined by the setter so that there is `offset` distance
        between the nodes
        """
        ipos = setter.getItemPos(items)
        order = sorted(list(range(len(ipos))), key=ipos)
        sizes = setter.getSizes(items)

        curPos = ipos[order[0]] - offset
        for idx in order:
            item = items[idx]
            setter.set(item, curPos + offset)
            curPos += sizes[idx] + offset

    @staticmethod
    def distribute(items, setter):
        """
        A funciton that distributes the given nodes between the current
        min and max percent slices along an axis determined by the given setter
        """
        ipos = setter.getItemPos(items)
        sizes = setter.getSizes(items)

        order = sorted(enumerate(ipos), key=lambda x: x[1])
        order, iposS = zip(*order)
        sizesS = [sizes[i] for i in order]

        start, stop = min(ipos), max(ipos) - sum(sizes) + sizes[0]
        step = (stop - start) / (len(ipos) - 1)

        newPosS = []
        accum = 0
        for i, s in enumerate(sizesS):
            newPosS.append(start + i * step + accum)
            accum += s

        newPos = [0.0] * len(ipos)
        for o, v in zip(order, newPosS):
            newPos[o] = v

        for v, item in zip(newPos, items):
            setter.set(item, v)

    @staticmethod
    def columnRowSwap(items):
        """ Swap columns to rows and vice versa"""
        p = [i.pos() for i in items]
        xy = [(i.x(), i.y()) for i in p]
        x, y = xy[0]
        x, y = (x - y, y - x)
        xy = [(a + x, b + y) for a, b in xy]
        for i, xy in zip(items, xy):
            i.setX(xy[1])
            i.setY(xy[0])

    @staticmethod
    def getDepNode(nodeName):
        mobj = om.MObject()
        selectionList = om.MSelectionList()
        try:
            selectionList.add(str(nodeName))
        except Exception:
            return None
        selectionList.getDependNode(0, mobj)
        fn = om.MFnDependencyNode(mobj)
        return fn

    @staticmethod
    def getAttrDict(dep):
        """ Read a depend node to get the top-level attrs """
        dd = {}
        afn = om.MFnAttribute()
        for i in range(dep.attributeCount()):
            a = dep.attribute(i)
            afn.setObject(a)
            dd[afn.name().lower()] = a
        return dd

    def getNodeDisplayedTopLevelAttrs(self, node):
        """ Get the top-level plug order shown in the node editor
        This should simply be from top to bottom

        Arguments:
            node (QGraphicsItem): The node editor graphics item to query

        Returns
            list: A list of maya Attributes/CompoundAttributes in the order
                that they are displayed on the node in the node editor

        """
        nodeName = self.getNodeName(node)
        dep = self.getDepNode(nodeName)
        adict = self.getAttrDict(dep)
        ci = node.childItems()
        if len(ci) < 2:
            return []
        treeItem = ci[1]
        nodeModel = treeItem.children()[0]
        root = nodeModel.index(-1, -1)
        cfn = om.MFnCompoundAttribute()
        ret = []
        for r in range(nodeModel.rowCount(root)):
            i = nodeModel.index(r, 0)
            name = nodeModel.data(i).replace(" ", "").lower()
            if name not in adict:
                continue
            attr = adict[name]
            fn = om.MFnCompoundAttribute if cfn.hasObj(attr) else om.MFnAttribute
            ret.append(fn(attr))
        return ret

    # TODO: write a function to get *all* node toplevel attrs
    # And if there are multiple nodes with the same name, then I need to
    # Do the stupid selection trick to correlate the MObjects with the GraphicsNodes

    def getCurrentState(self):
        """ Get the total state of the current graph """
        items = self.getAllItems()
        posDict = {}
        # TODO: Handle multiple nodes with the same name
        for node in items:
            nn = self.getNodeName(node)
            r = node.sceneBoundingRect()
            posDict[nn] = (r.x(), r.y(), r.width(), r.height())
        return posDict

    def getAllNodeNames(self):
        """ Get the full names of all the nodes in the current node editor """
        allNodeNames = cmds.ls(
            cmds.nodeEditor(self.name, getNodeList=True, query=True), long=True
        )
        return allNodeNames

    def getAllNodeObjects(self):
        """ Get all the Qt node objects keyed by their names """
        allNodeNames = self.getAllNodeNames()
        nnDict = {}
        with restoreSel():
            for nn in allNodeNames:
                cmds.select(nn)
                sel = self.getSelItems()
                if sel:
                    nnDict[nn] = sel[0]
        return nnDict

    def getAllTopLevelAttrs(self, allNodeNames=None):
        """ Get all the top-level attributes currently displayed in the Node Editor

        Arguments:
            allNodeNames (list, optional): The list of nodes to check. These should
                be full names. If not supplied then check all the nodes

        Returns:
            dict: A dict of {nodeFullName: [MFnAttribute, ...]}

        """
        allNodeNames = allNodeNames or self.getAllNodeNames()

        ret = {}
        for nodeName, node in allNodeNames.iteritems():
            dep = self.getDepNode(nodeName)
            adict = self.getAttrDict(dep)
            # childItems should return the simpleText name item
            # and the node's graphicsWidget tree if it exists
            ci = node.childItems()
            if len(ci) < 2:
                ret[nodeName] = []
                continue
            treeItem = ci[1]
            # The first child of the tree is its model
            nodeModel = treeItem.children()[0]
            root = nodeModel.index(-1, -1)
            cfn = om.MFnCompoundAttribute()
            retVal = []
            for r in range(nodeModel.rowCount(root)):
                i = nodeModel.index(r, 0)
                name = nodeModel.data(i).replace(" ", "").lower()
                if name not in adict:
                    continue
                attr = adict[name]
                fn = om.MFnCompoundAttribute if cfn.hasObj(attr) else om.MFnAttribute
                retVal.append(fn(attr))
            ret[nodeName] = retVal
        return ret

    def buildFullTree(self, cnx):
        """ Given a dictionary of {node->[direct connections]}, build a dictionary
        of {node->[All Downstreams]}. Also detect cycles while we're in there

        Arguments:
            cnx (dict): The dictionary of direct connections

        Returns:
            dict: Dictionary of fully recursive connections
            list: List of cycles encountered
        """

        def _buildFullTree(k, cnx, ret, path, cycles, depth=0):
            if k in path:
                cycles.append(set(path[path.index(k) :]))
            elif k not in ret:
                fts = set()
                p = path + [k]
                for ups in cnx[k]:
                    fts |= _buildFullTree(ups, cnx, ret, p, cycles, depth + 1)
                ret[k] = fts
                return set([k]) | ret.get(k, set())
            return set([k])

        ret = {}
        cycles = []
        for k in cnx.keys():
            _buildFullTree(k, cnx, ret, [], cycles)

        # Turn the cycles into dicts so I can quickly access them
        # based off the current object
        cDict = {}
        for cy in cycles:
            for c in cy:
                cDict[c] = cy

        dDict = {}
        for k, v in ret.iteritems():
            dDict[k] = v - set([k])

        return dDict, cDict

    def getStreams(self, allNodeNames=None, curNodeEd=None):
        allNodeNames = allNodeNames or self.getAllNodeNames()
        nnset = set(allNodeNames)
        # For all those objects get the up/down streams limited by the current panel
        ups, downs = {}, {}
        for k in nnset:

            ucnx = cmds.listConnections(k, destination=False, shapes=True) or []
            ucnx = cmds.ls(ucnx, long=True) or []
            ups[k] = sorted(set(ucnx) & nnset)

            dcnx = cmds.listConnections(k, source=False, shapes=True) or []
            dcnx = cmds.ls(dcnx, long=True) or []
            downs[k] = sorted(set(dcnx) & nnset)

        return ups, downs

    def buildTreeLayers(self):
        """ For a given node editor, determine the right-to-left "layers" for layout
        This *should* build the exact same layers as the built-in layout command

        Returns:
            list: An ordered list of unordered layers

        """
        ups, downs = self.getStreams()
        fullDowns, downCycles = self.buildFullTree(downs)
        seeds = sorted(set([k for k, v in downs.iteritems() if not v]))

        tree = [seeds[:]]
        memo = set(copy.copy(tree[0]))
        for _ in range(2048):
            layer = set()
            for s in tree[-1]:
                layer |= set(ups[s])

            if not layer:
                break
            layer -= memo
            # Look through the objects in the current layer
            # Any of them that have all their downstreams
            # currently in the tree can be added
            adc = set()
            for i in layer:
                adc |= downCycles.get(i, set())

            newLayer = []
            for i in layer:
                fd = fullDowns[i] - adc
                if not (fd - memo):
                    newLayer.append(i)

            if not newLayer:
                break
            tree.append(newLayer)
            memo.update(newLayer)
        else:
            raise RuntimeError("Recursion Too Deep")

        return tree

    @staticmethod
    def separateTrees(multiTree, fullUps):
        """ Given the all-in-one tree from buildTreeLayers, separate the tree into
        interconnected graphs
        """
        seeds = {frozenset([i]): fullUps[i] for i in multiTree[-1]}
        for _ in xrange(1024):
            newSeeds = {}
            found = False
            for ka, va in seeds.iteritems():
                for kb, vb in seeds.iteritems():
                    # If the keys are the same object, skip
                    if ka is kb:
                        continue
                    # If there is a value overlap
                    if va & vb:
                        found = True
                        newSeeds[ka | kb] = va | vb
            seeds = newSeeds
            if not found:
                break
        else:
            raise RuntimeError("Too Many Iterations")


# TODO


def sortTreeLayers(tree, ups, curNodeEd=None):
    """ Sort the given tree layers top-to-bottom """
    allNodeNames = set()
    for layer in tree:
        allNodeNames |= layer
    tlaDict = getAllTopLevelAttrs(allNodeNames=allNodeNames, curNodeEd=curNodeEd)


def layoutTreeLayers(tree):
    """ Determine the real vertical positions of the nodes in the given tree
    that will make a straighter, more readable graph 
    """


# tla = getAllTopLevelAttrs()
# align(getSelItems(), ySetter, prc=1.0)
# distribute(getSelItems(), xSetter)
