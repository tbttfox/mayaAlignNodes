from __future__ import print_function
from maya import OpenMayaUI as mui, cmds
from PySide2.QtWidgets import QGraphicsItem, QWidget, QGraphicsView
from shiboken2 import wrapInstance
import sys
if sys.version_info.major == 3:
    long = int


def getNodeEdUI():
    """ Get the maya node editor ui widgets """

    pan = cmds.getPanel(scriptType="nodeEditorPanel")[0]
    edName = pan + "NodeEditorEd"
    edTab = cmds.nodeEditor(edName, activeTab=True, query=True)

    nodeEdPane = wrapInstance(
        long(mui.MQtUtil.findControl(edTab)), QWidget,
    )
    nodeEdGraphView = nodeEdPane.findChild(QGraphicsView)
    nodeEdScene = nodeEdGraphView.scene()
    return nodeEdGraphView, nodeEdScene


def getSelItems():
    """ Get the nodes selected in the UI panel """
    nodeEdGraphView, nodeEdScene = getNodeEdUI()
    items = nodeEdScene.selectedItems()
    items = [i for i in items if isinstance(i, QGraphicsItem)]
    return items


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
    def getItemPos(self, items):
        return [i.pos().x() for i in items]

    @staticmethod
    def getSizes(self, items):
        return [i.sceneBoundingRect().width() for i in items]


class ySetter(object):
    """ A class that handles getting/setting the Y values
    of a group of objects with a consistent interface
    """

    @staticmethod
    def set(item, val):
        item.setY(val)

    @staticmethod
    def getItemPos(self, items):
        return [i.pos().y() for i in items]

    @staticmethod
    def getSizes(self, items):
        return [i.sceneBoundingRect().height() for i in items]


def align(items, setter, prc):
    """ A funciton that aligns the center lines of a group of items
    along an axis determined by the given setter
    """
    ipos = setter.getItemPos(items)
    minX, maxX = min(ipos), max(ipos)
    for j in items:
        setter.set(j, (minX * prc) + (maxX * (1.0 - prc)))


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


def distribute(items, setter, prc):
    """
    A funciton that distributes the given nodes between the current
    min and max percent slices along an axis determined by the given setter
    """
    ipos = setter.getItemPos(items)
    sizes = setter.getSizes(items)
    dpos = [int(v + (prc * w)) for v, w in zip(ipos, sizes)]
    rest = [d - i for d, i in zip(dpos, ipos)]
    order = sorted(range(len(rest)), key=rest)

    start, stop = rest[order[0]], rest[order[-1]]
    num = len(items)
    ovals = [(stop * i + start * (num - i - 1)) / (num - 1) for i in range(num)]

    for i, item in enumerate(items):
        setter.set(item, ovals[order[i]] - rest[i])


def columnRowSwap(items):
    """ Swap columns to rows and vice versa"""
    p = [i.pos() for i in items]
    xy = [(i.x(), i.y()) for i in p]
    x, y = xy[0]
    x, y = (x-y, y-x)
    xy = [(a+x, b+y) for a, b in xy]
    for i, xy in zip(items, xy):
        i.setX(xy[1])
        i.setY(xy[0])


def getNodePlugOrder(node, cnx):
    """ Get the plug order shown in the node editor
    This should simply be from top to bottom, and should
    only include currently plugged indices

    Arguments:
        node (str): The node to get the order from
        cnx (list): The list of nodes to check the connections of

    Returns:
        (list): The ordered list of input connections of the node
        (list): The ordered list of output connections from the node
        (list): A list of unconnected nodes
    """
    # First get plugged indices
    # Then get the node display type (1,2,3 or custom(4))
    # if 1/2/3, then use the node default order
    # if 4, then read the user custom order
    # if there are nodes that *aren't* in the custom order
    # fall back on the default order
    pass


def getNodeUpstreams(node):
    """ Get the connected upstreams shown in the current graph """
    pass


def getCurrentState():
    """ Get the total state of the current graph """
    nodeEdGraphView, nodeEdScene = getNodeEdUI()

