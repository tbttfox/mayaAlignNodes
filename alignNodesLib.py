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
import re

if sys.version_info.major == 3:
    long = int


def _plugNatSort(ls):
    """ Naturalsort by the first item in a tuple
    Adapted from: http://blog.codinghorror.com/sorting-for-humans-natural-sort-order/
    This could definitely be more generic, but it's probably not worth the time
    """

    def convert(text):
        return int(text) if text.isdigit() else text.lower()

    def alphanum_key(key):
        return [convert(c) for c in re.split('([0-9]+)', key[0])]

    return sorted(ls, key=alphanum_key)


def _flatToTuples(flat, count=2):
	ff = iter(flat)
	return zip(*[ff]*count)


def _dedup(items):
    memo = set()
    out = []
    for i in items:
        if i not in memo:
            out.append(i)
            memo.add(i)
    return out


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
        self._ups = None
        self._fullUps = None
        self._downs = None
        self._fullDowns = None
        self._cycles = None

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

    def getStreams(self, allNodeNames=None):
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

    @staticmethod
    def _buildFullTree(cnx):
        """ Given a dictionary of {node->[direct connections]}, build a dictionary
        of {node->[All Downstreams]}. Also detect cycles while we're in there

        Arguments:
            cnx (dict): The dictionary of direct connections

        Returns:
            dict: Dictionary of fully recursive connections
            list: List of cycles encountered
        """

        def _bft(k, cnx, ret, path, cycles, depth=0):
            if k in path:
                cycles.append(set(path[path.index(k) :]))
            elif k not in ret:
                fts = set()
                p = path + [k]
                for ups in cnx[k]:
                    fts |= _bft(ups, cnx, ret, p, cycles, depth + 1)
                ret[k] = fts
            return set([k]) | ret.get(k, set())

        ret = {}
        cycles = []
        for k in cnx.keys():
            _bft(k, cnx, ret, [], cycles)

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

    @property
    def ups(self):
        if self._ups is None:
            self._ups, self._downs = self.getStreams()
        return self._ups

    @property
    def downs(self):
        if self._downs is None:
            self._ups, self._downs = self.getStreams()
        return self._downs

    @property
    def fullUps(self):
        if self._fullUps is None:
            self._fullUps, cycles = self._buildFullTree(self.ups)
            if self._cycles is None:
                self._cycles = cycles
        return self._fullUps

    @property
    def fullDowns(self):
        if self._fullDowns is None:
            self._fullDowns, cycles = self._buildFullTree(self.downs)
            if self._cycles is None:
                self._cycles = cycles
        return self._fullDowns

    @property
    def cycles(self):
        if self._cycles is None:
            # If cycles is None, then neither fullUps/fullDowns has been called
            # So, if I'm gonna compute it anyway, may as well store it for later
            # The buildTreeLayers call uses the fullDownstreams, so may as well
            # compute that one
            self._fullDowns, self._cycles = self._buildFullTree(self.downs)
        return self._cycles

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

    def getCurrentState(self, nodeDict=None):
        """ Get the total state of the current graph """
        posDict = {}
        nodeDict = nodeDict or self.getAllNodeObjects()
        for nn, node in nodeDict.iteritems():
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

    def getAllTopLevelAttrs(self, allNodeObjects=None):
        """ Get all the top-level attributes currently displayed in the Node Editor

        Arguments:
            allNodeObjects (list, optional): The list of nodes to check. These should
                be full names. If not supplied then check all the nodes

        Returns:
            dict: A dict of {nodeFullName: [MFnAttribute, ...]}

        """
        allNodeObjects = allNodeObjects or self.getAllNodeObjects()

        ret = {}
        for nodeName, node in allNodeObjects.iteritems():
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

    def buildTreeLayers(self, seeds):
        """ For a given node editor, determine the right-to-left "layers" for layout
        This *should* build the exact same layers as the built-in layout command
        Arguments:
            seeds (list): A list of items to get the upstreams of

        Returns:
            list: An ordered list of unordered layers
        """
        # seeds = sorted(set([k for k, v in self.downs.iteritems() if not v]))

        tree = [seeds[:]]
        memo = set(copy.copy(tree[0]))
        for _ in range(2048):
            layer = set()
            for s in tree[-1]:
                layer |= set(self.ups[s])

            if not layer:
                break
            layer -= memo
            # Look through the objects in the current layer
            # Any of them that have all their downstreams
            # currently in the tree can be added
            adc = set()
            for i in layer:
                adc |= self.cycles.get(i, set())

            newLayer = []
            for i in layer:
                fd = self.fullDowns[i] - adc
                if not (fd - memo):
                    newLayer.append(i)

            if not newLayer:
                break
            tree.append(sorted(newLayer))
            memo.update(newLayer)
        else:
            raise RuntimeError("Recursion Too Deep")

        return tree

    @staticmethod
    def getTreeSeeds(seeds, fullUps):
        """ Given a list of seed items, group them so that any pair of items in
        a group share at least one upstream

        Arguments:
            seeds (list): A list of the right-most items in the node editor tree
                These items shuld have upstreams, but not downstreams.
                ie. self.buildTreeLayers()[0]
            fullUps (dict): The self.fullUps dictionary

        Returns:
            list: A list of lists of layer-0 tree items. The upstreams of each set
                set together form a full interconnected tree.
        """
        # Basically, loop through the seeds to find overlapping values
        # When we find an overlapping value, merge them, and restart
        # the whole process. If we make it through the whole process
        # without finding a merge, then we can return
        # Note: If a for-loop ends from a break, the else *isn't* run

        seeds = {frozenset([i]): fullUps[i] for i in seeds}
        for _ in xrange(1024):
            items = seeds.items()
            for ka, va in items:
                for kb, vb in items:
                    if ka is kb:
                        continue
                    if va & vb:
                        del seeds[ka]
                        del seeds[kb]
                        seeds[ka | kb] = va | vb
                        break  # GOTO A
                else:
                    continue
                # A
                break  # GOTO B
            else:
                break  # GOTO C
            # B
        else:
            raise RuntimeError("Too Many Iterations")
        # C
        return map(sorted, seeds.keys())

    def reorderInputs(self, node, inputs, topLevelAttrDict):
        """ Given a node and its inputs, reorder the inputs to match the
        current attribute order """
        tlaNames = [i.name() for i in topLevelAttrDict.get(node, [])]
        if not tlaNames:
            return inputs

        aliases = cmds.aliasAttr(node, query=True) or []
        aliases = ["{0}.{1}".format(node, i) for i in aliases]
        aliases = dict(_flatToTuples(aliases))

        ucnx = cmds.ls(
            cmds.listConnections(
                node, destination=False, shapes=True, plugs=True, connections=True
            )
            or [],
            long=True,
        )

        ucnx = [aliases.get(i, i) for i in ucnx]
        allPairs = _flatToTuples(ucnx)
        pairs = [i for i in allPairs if i[1].split('.')[0] in inputs]

        # `pairs` is now structured as [(inPlug, outPlug), ...]
        # Note: the order is *backwards*

        # Build the plug names
        plugNames = ["{0}.{1}".format(node, i) for i in tlaNames]

        #aplugs = [[p for p in pairs if p[0].startswith(x)] for x in plugNames]
        aplugs = [[p for p in pairs if re.match(x+r'\b', p[0])] for x in plugNames]
        aplugs = [_plugNatSort(a) for a in aplugs if a]
        aplugs = [i[1] for sublist in aplugs for i in sublist]
        aplugs = [i.split('.')[0] for i in aplugs]
        xinputs = [i for i in inputs if i not in aplugs]
        return _dedup(xinputs + aplugs)

    def reorderLayer(self, prev, layer, topLevelAttrDict):
        """ Starting from the previous layer, get the order for the new layer """
        # Get the possibly repeated chunks
        chunks = []
        memo = set()
        for p in prev:
            chunk = [i for i in self.ups[p] if i in layer]
            chunk = self.reorderInputs(p, chunk, topLevelAttrDict)
            chunk = [i for i in chunk if i not in memo]
            # Only keep nodes the first time they're encountered
            # Later: Maybe average where they connect in the list
            # and put them closer to the "middle"
            memo.update(chunk)
            chunks.append(chunk)
        # Flatten the array of chunks
        return [i for sublist in chunks for i in sublist]

    def sortTreeLayers(self, tree):
        """ Sort the given tree layers top-to-bottom """
        ano = self.getAllNodeObjects()
        allNodeObjects = {}
        for layer in tree:
            for item in layer:
                allNodeObjects[item] = ano[item]

        topLevelAttrDict = self.getAllTopLevelAttrs(allNodeObjects=allNodeObjects)

        newTree = [tree[0][:]]
        for i in range(1, len(tree)):
            layer = self.reorderLayer(newTree[-1], tree[i], topLevelAttrDict)
            newTree.append(layer)
        return newTree

    def naiveLayoutTreeLayers(self, tree):
        """ Determine the real vertical positions of the nodes in the given tree
        that will make a straighter, more readable graph
        This naive version just stacks things in layers, and nothing else
        """

        nodeDict = self.getAllNodeObjects()
        state = self.getCurrentState(nodeDict=nodeDict)

        hSpacing = 100
        vSpacing = 50
        cx = 0
        for layer in reversed(tree):
            cw, ch = 0, 0
            for item in layer:
                x, y, w, h = state[item]
                node = nodeDict[item]
                node.setY(ch)
                node.setX(cx)
                cw = max(cw, w)
                ch += h + vSpacing
            cx += cw + hSpacing

    # TODO
    def layoutTreeLayers(self, tree):
        """ Determine the real vertical positions of the nodes in the given tree
        that will make a straighter, more readable graph
        """
        pass

    # TODO
    def placeNodes(self, trees):
        """ Given a list of placed trees, find their bounding boxes, get the real
        node position values, and actually set the data on the Qt items
        """
        pass

    def layout(self):
        """ Lay out a node editor, taking the order of the plugs into account """
        seeds = sorted(set([k for k, v in self.downs.iteritems() if not v]))
        seeds = self.getTreeSeeds(seeds, self.fullUps)
        trees = [self.buildTreeLayers(s) for s in seeds]
        trees = [self.sortTreeLayers(t) for t in trees]
        for t in trees:
            self.naiveLayoutTreeLayers(t)

        #trees = [self.layoutTreeLayers(t) for t in trees]
        #self.placeNodes(trees)


NodeEditorUI().layout()

