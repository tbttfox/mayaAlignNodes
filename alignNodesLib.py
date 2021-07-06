'''

"""
Adds outgoing connections for a specific attribute (under the cursor) to the Node Editor.

1. Gets the plug that the cursor is hovering over
2. Gets direct output connections (conversion nodes and their outputs if necessary)
3. Adds these nodes to the Node Editor

This should obviously only be executed while hovering over the attribute in the Node Editor. 
To test you could: 
    * assign it to a hotkey
    * make it a shelf button, execute once and then hit "g" to execute again
so it is executed while you hover over attributes in the Node Editor
"""
from maya import mel
from maya import cmds
node_editor = mel.eval("getCurrentNodeEditor")
item_under_cursor = cmds.nodeEditor(node_editor, feedbackType=True, q=True)
if item_under_cursor == "plug":
    plug_under_cursor = cmds.nodeEditor(node_editor, feedbackPlug=True, q=True)
    # outgoing connections could obviously be changed to incoming connections, ...
    all_out_con = cmds.listConnections(plug_under_cursor, s=False, d=True, scn=True) or []
    all_out_con.extend(
        cmds.listConnections(plug_under_cursor, s=False, d=True, scn=False) or [])
    all_out_con = list(set(all_out_con)) # deduplicate
    if all_out_con:
        cmds.nodeEditor(node_editor, addNode=all_out_con, layout=False, e=True)
    else:
        cmds.warning("Attribute '{}' has no outgoing connections.".format(plug_under_cursor))
else:
    cmds.warning("Hover over attribute in Node Editor while executing.")

# Get all nodes displayed in the editor
cmds.nodeEditor(getNodeList=True, query=True)

# Specifies a function to be called whenever the contents of the node editor changes.
cmds.nodeEditor(contentsChangedCommand=lambda x: x)

# Write out the current node editor to a DOT format file
# This does *NOT* store plug-level connections
# Nor does it store node positions ... so it's kinda useless for me
filePath = ""
cmds.nodeEditor(dotFormat=filePath, query=True)
# Read a DOT file format filepath
cmds.nodeEditor(dotFormat=filePath, edit=True)

# Specifies a function to override the default action when a graph layout is required.
cmds.nodeEditor(layoutCommand=lambda x: x)

# Select all items up/down stream to the currently active selection.
cmds.nodeEditor(selectUpstream=True)
cmds.nodeEditor(selectDownstream=True)



# user prefs templates are in prefs/viewTemplates/NE<nodeType>Template.xml
# C:/Users/tyler/Documents/maya/2022_MultiPref/prefs/viewTemplates/NEtransformTemplate.xml
# XML: <templates>/<view>/(<property>, ...) Read the names of the properties to get all the attrs in order
# ... otherwise, getting a list of attributes from a node type is done via the api
# you can list plugs using: MFnDependencyNode::attributeCount() / MFnDependencyNode::attribute()
'''


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


def getNodeEdUI():
    """ Get the maya node editor ui Qt widgets

    Returns:
        QGraphicsView: The view widget for the node editor
        QGraphicsScene: The current scene loaded into the view

    """
    pan = cmds.getPanel(scriptType="nodeEditorPanel")[0]
    edName = pan + "NodeEditorEd"
    ctrl = mui.MQtUtil.findControl(edName)
    if ctrl is None:
        raise RuntimeError("Node editor is not open")
    nodeEdPane = wrapInstance(long(ctrl), QWidget)
    stack = nodeEdPane.findChild(QStackedLayout)
    nodeEdGraphView = stack.currentWidget().findChild(QGraphicsView)
    nodeEdScene = nodeEdGraphView.scene()
    return nodeEdGraphView, nodeEdScene


def getSelItems(curNodeEd=None):
    """ Get the nodes selected in the UI panel

    Returns:
        list(QGraphicsItem): The selected items in the current editor tab
    """
    nodeEdGraphView, nodeEdScene = curNodeEd or getNodeEdUI()
    items = nodeEdScene.selectedItems()
    # There are also
    # QGraphicsPathItems (The connection lines)
    # QGraphicsSimpleTextItem (The node names)
    # QGraphicsWidget (The sub-sections of each node, like the tree and filter lines)
    items = [i for i in items if type(i) is QGraphicsItem]
    return items


def getAllItems(curNodeEd=None):
    """ Get all nodes in the UI panel

    Returns:
        list(QGraphicsItem): The nodes in the current editor tab
    """
    nodeEdGraphView, nodeEdScene = curNodeEd or getNodeEdUI()
    items = nodeEdScene.items()
    items = [i for i in items if type(i) is QGraphicsItem]
    return items


def getNodeName(node):
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


def getItemPos(items):
    """ Get the x/y positions of the given UI items in the node editor """
    nodePosList = []
    for i in items:
        nodePosList.append([i.pos().x(), i.pos().y()])
    return nodePosList


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


def getAttrDict(dep):
    """ Read a depend node to get the top-level attrs """
    dd = {}
    afn = om.MFnAttribute()
    for i in range(dep.attributeCount()):
        a = dep.attribute(i)
        afn.setObject(a)
        dd[afn.name().lower()] = a
    return dd


def getNodeDisplayedTopLevelAttrs(node):
    """ Get the top-level plug order shown in the node editor
    This should simply be from top to bottom

    Arguments:
        node (QGraphicsItem): The node editor graphics item to query

    Returns
        list: A list of maya Attributes/CompoundAttributes in the order
            that they are displayed on the node in the node editor

    """
    nodeName = getNodeName(node)
    dep = getDepNode(nodeName)
    adict = getAttrDict(dep)
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


def getCurrentState():
    """ Get the total state of the current graph """
    items = getAllItems()
    posDict = {}
    # TODO: Handle multiple nodes with the same name
    for node in items:
        nn = getNodeName(node)
        r = node.sceneBoundingRect()
        posDict[nn] = (r.x(), r.y(), r.width(), r.height())
    return posDict


def getNodeUpstreams(node):
    """ Get the connected upstreams shown in the current graph """
    cmds.nodeEditor(selectUpstream=True)


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


def getAllNodeNames(curNodeEd=None):
    curNodeEd = curNodeEd or getNodeEdUI()
    nodes = getAllItems(curNodeEd=curNodeEd)
    nnDict = {}
    with restoreSel():
        for node in nodes:
            nn = getNodeName(node)
            objs = cmds.ls(nn, long=True)
            if not objs:
                continue
            elif len(objs) == 1:
                nnDict[objs[0]] = node
            else:
                for obj in objs:
                    cmds.select(obj)
                    sel = getSelItems(curNodeEd=curNodeEd)
                    if sel:
                        nnDict[obj] = sel[0]
    return nnDict


def getAllTopLevelAttrs(allNodeNames=None, curNodeEd=None):
    curNodeEd = curNodeEd or getNodeEdUI()
    allNodeNames = allNodeNames or getAllNodeNames(curNodeEd=curNodeEd)

    ret = {}
    for nodeName, node in allNodeNames.iteritems():
        dep = getDepNode(nodeName)
        adict = getAttrDict(dep)
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


# tla = getAllTopLevelAttrs()
# align(getSelItems(), ySetter, prc=1.0)
# distribute(getSelItems(), xSetter)


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


def buildFullTree(cnx):
    """ Given a dictionary of {node->[direct connections]}, build a dictionary
    of {node->[All Downstreams]}. Also detect cycles while we're in there

    Arguments:
        cnx (dict): The dictionary of direct connections

    Returns:
        dict: Dictionary of fully recursive connections
        list: List of cycles encountered
    """
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


def buildTreeLayers():
    pan = cmds.getPanel(scriptType="nodeEditorPanel")[0]
    edName = pan + "NodeEditorEd"
    allNodeNames = cmds.ls(
        cmds.nodeEditor(edName, getNodeList=True, query=True), long=True
    )
    nnset = set(allNodeNames)

    # For all those objects get the up/down streams limited by the current panel
    ups, downs = {}, {}
    for k in nnset:
        ucnx = (
            cmds.ls(
                cmds.listConnections(k, destination=False, shapes=True) or [], long=True
            )
            or []
        )
        ups[k] = sorted(set(ucnx) & nnset)
        dcnx = (
            cmds.ls(cmds.listConnections(k, source=False, shapes=True) or [], long=True)
            or []
        )
        downs[k] = sorted(set(dcnx) & nnset)

    fullUps, upCycles = buildFullTree(ups)
    fullDowns, downCycles = buildFullTree(downs)
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
