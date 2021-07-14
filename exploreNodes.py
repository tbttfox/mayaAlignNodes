"""
Add right-click menus to the node editor for quickly exploring node connections
Add an option to somehow drag an item and all its upstreams??
Add Scene UNDOS!!!

"""


from maya import OpenMayaUI as mui, OpenMaya as om, cmds
from PySide2.QtWidgets import (
    QGraphicsItem,
    QWidget,
    QGraphicsView,
    QStackedLayout,
    QGraphicsSimpleTextItem,
    QGraphicsSceneMouseEvent,
)
from PySide2.QtCore import QObject, QEvent, Qt
from PySide2.QtGui import QMouseEvent, QKeyEvent

class MyFilter(QObject):
    def __init__(self, name):
        super(MyFilter, self).__init__()
        self._edname = name

    def eventFilter(self, obj, event):
        etype = event.type()
        if isinstance(event, QGraphicsSceneMouseEvent):
            if event.button() == Qt.RightButton:
                mods = event.modifiers()
                shift = "Shift " if bool(mods & Qt.ShiftModifier) else ""
                ctrl = "Ctrl " if bool(mods & Qt.ControlModifier) else ""
                nn = cmds.nodeEditor(self._edname, feedbackPlug=True, query=True)
                print ctrl + shift + "RIGHT CLICK", nn, etype

        return False # I didn't handle it

nui = NodeEditorUI()
ef = MyFilter(nui.name)
nui.scene.removeEventFilter(ef)

