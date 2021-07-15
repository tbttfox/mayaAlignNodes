

from maya import OpenMaya as om, cmds
from PySide2.QtWidgets import QGraphicsSceneMouseEvent, QListWidget
from PySide2.QtCore import QObject, Qt, QPoint
from PySide2.QtGui import QCursor
import shiboken2
from functools import partial

def clickMenu(funcs, wid, item):
    funcs[wid.row(item)]()

def showMenu(keys, funcs, side, par):
    pos = par.mapFromGlobal(QCursor.pos())
    menu = QListWidget(parent=par)

    for key, func in zip(keys, funcs):
        menu.addItem(key)
    menu.itemPressed.connect(partial(clickMenu, funcs, menu))

    width = menu.sizeHintForColumn(0) + 2 * menu.frameWidth() + 5
    height = menu.sizeHintForRow(0) * len(keys) + 2 * menu.frameWidth() + 5

    menu.resize(width, height)

    if side == "left":
        xval = pos.x() - width - 5
    else:
        xval = pos.x() + 5
    yval = pos.y() - height / 2.0

    menu.move(QPoint(xval, yval))
    menu.show()
    return menu



class MyFilter(QObject):
    def __init__(self, name, scene):
        super(MyFilter, self).__init__()
        self._edname = name
        self._scene = scene
        self._inMenu = None
        self._outMenu = None

    def eventFilter(self, obj, event):
        if isinstance(event, QGraphicsSceneMouseEvent):
            if event.button() == Qt.RightButton:
                mods = event.modifiers()
                shift = bool(mods & Qt.ShiftModifier)
                ctrl = bool(mods & Qt.ControlModifier)
                plug = cmds.nodeEditor(self._edname, feedbackPlug=True, query=True)
                if (ctrl or shift) and plug:
                    addRem = "-"
                    func = self.remItems
                    if shift:
                        addRem = "+"
                        func = self.addItems

                    self.clearMenu(self._inMenu)
                    self.clearMenu(self._outMenu)
                    pn = plug.split('.', 1)[-1]

                    inputs, outputs = self.getAllConnections(plug)
                    if inputs:
                        key = "{2}.{0} ({1})".format(pn, len(inputs), addRem)
                        self._inMenu = showMenu([key], [lambda: func(inputs)], "left", self._scene)
                    if outputs:
                        key = "{2}.{0} ({1})".format(pn, len(outputs), addRem)
                        self._outMenu = showMenu([key], [lambda: func(outputs)], "right", self._scene)
                    return True

        return False  # I didn't handle it

    @staticmethod
    def clearMenu(menu):
        if menu is not None and shiboken2.isValid(menu):
            menu.hide()
            menu.deleteLater()
            menu = None

    @staticmethod
    def unalias(plug, aliases):
        nn, an = plug.split('.', 1)
        an = aliases.get(an, an)
        return '.'.join([nn, an])

    @staticmethod
    def isPlugChildOf(par, child):
        if par == child:
            return True
        while True:
            if child.isChild():
                child = child.parent()
            elif child.isElement():
                child = child.array()
            else:
                return False
            if par == child:
                return True

    @classmethod
    def getAllConnections(cls, plug):
        sl = om.MSelectionList()
        sl.add(plug)
        clickPlug = om.MPlug()
        sl.getPlug(0, clickPlug)

        node = om.MObject()
        sl.getDependNode(0, node)
        fn = om.MFnDependencyNode(node)
        nodeplugs = om.MPlugArray()
        fn.getConnections(nodeplugs)
        inputs, outputs = [], []

        for i in range(nodeplugs.length()):
            plug = nodeplugs[i]
            if cls.isPlugChildOf(clickPlug, plug):
                inCnx = om.MPlugArray()
                outCnx = om.MPlugArray()
                plug.connectedTo(inCnx, True, False)
                plug.connectedTo(outCnx, False, True)
                for j in range(inCnx.length()):
                    fn.setObject(inCnx[j].node())
                    inputs.append(fn.name())
                for j in range(outCnx.length()):
                    fn.setObject(outCnx[j].node())
                    outputs.append(fn.name())
        return inputs, outputs

    def addItems(self, items):
        self.clearMenu(self._inMenu)
        self.clearMenu(self._outMenu)
        for i in items:
            cmds.nodeEditor(self._edname, edit=True, addNode=i)
        cmds.select(items, noExpand=True, replace=True)

    def remItems(self, items):
        self.clearMenu(self._inMenu)
        self.clearMenu(self._outMenu)
        for i in items:
            cmds.nodeEditor(self._edname, edit=True, removeNode=i)


if not shiboken2.isValid(nui.scene):
    nui = NodeEditorUI()

try:
    nui.scene.removeEventFilter(ef)
    print "Removing Event Filter"
    del ef
except NameError:
    nui = NodeEditorUI()
    ef = MyFilter(nui.name, nui.graphView)
    nui.scene.installEventFilter(ef)
    print "Adding Event Filter"

