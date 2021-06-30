from PySide2 import QtCore, QtGui, QtWidgets
import maya.OpenMayaUI as mui
import maya.cmds as mc
import maya.mel as mm
from shiboken2 import wrapInstance
import images




class alignNodesUI(QtWidgets.QWidget, alignNodesUI_DockWidget):
    def __init__(self, parent=getMayaWindow()):
        QtWidgets.QWidget.__init__(self, parent)
        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setupUi(self)

    def getNodeEdUI(self):
        nodeEdPane = wrapInstance(
            long(mui.MQtUtil.findControl("nodeEditorPanel1NodeEditorEd")),
            QtWidgets.QWidget,
        )
        nodeEdGraphViewAttr = nodeEdPane.findChild(QtWidgets.QGraphicsView)
        nodeEdSceneAttr = nodeEdGraphViewAttr.scene()
        return nodeEdGraphViewAttr, nodeEdSceneAttr

    def horizontalAlignLeftFn(self, event):
        nodeEdGraphView, nodeEdScene = self.getNodeEdUI()

        # Collect Items In Scene
        # nodeEdSceneItems = nodeEdScene.items()
        nodeEdSceneItems = nodeEdScene.selectedItems()

        nodePosList = []
        for i in nodeEdSceneItems:
            if type(i) == QtWidgets.QGraphicsItem:
                nodePosList.append([i.pos().x(), i.pos().y()])
        # Get minimum in X Axis
        minX = min([i[0] for i in nodePosList])

        for j in nodeEdSceneItems:
            if type(j) == QtWidgets.QGraphicsItem:
                j.setX(minX)

    def horizontalAlignRightFn(self, event):
        nodeEdGraphView, nodeEdScene = self.getNodeEdUI()

        # Collect Items In Scene
        nodeEdSceneItems = nodeEdScene.selectedItems()

        nodePosList = []
        for i in nodeEdSceneItems:
            if type(i) == QtWidgets.QGraphicsItem:
                nodePosList.append([i.pos().x(), i.pos().y()])
        # Get minimum in X Axis
        maxX = max([i[0] for i in nodePosList])

        for j in nodeEdSceneItems:
            if type(j) == QtWidgets.QGraphicsItem:
                j.setX(maxX)

    def horizontalAlignCenterFn(self, event):
        nodeEdGraphView, nodeEdScene = self.getNodeEdUI()

        # Collect Items In Scene
        nodeEdSceneItems = nodeEdScene.selectedItems()

        nodePosList = []
        for i in nodeEdSceneItems:
            if type(i) == QtWidgets.QGraphicsItem:
                nodePosList.append([i.pos().x(), i.pos().y()])
        # Get minimum in X Axis
        minX = min([i[0] for i in nodePosList])
        maxX = max([i[0] for i in nodePosList])

        for j in nodeEdSceneItems:
            if type(j) == QtWidgets.QGraphicsItem:
                j.setX(((minX + maxX) / 2))

    def verticalAlignTopFn(self, event):
        nodeEdGraphView, nodeEdScene = self.getNodeEdUI()

        # Collect Items In Scene
        nodeEdSceneItems = nodeEdScene.selectedItems()

        nodePosList = []
        for i in nodeEdSceneItems:
            if type(i) == QtWidgets.QGraphicsItem:
                nodePosList.append([i.pos().x(), i.pos().y()])
        # Get minimum in X Axis
        minY = min([i[1] for i in nodePosList])

        for j in nodeEdSceneItems:
            if type(j) == QtWidgets.QGraphicsItem:
                j.setY(minY)

    def verticalAlignBottomFn(self, event):
        nodeEdGraphView, nodeEdScene = self.getNodeEdUI()

        # Collect Items In Scene
        nodeEdSceneItems = nodeEdScene.selectedItems()

        nodePosList = []
        for i in nodeEdSceneItems:
            if type(i) == QtWidgets.QGraphicsItem:
                nodePosList.append([i.pos().x(), i.pos().y()])
        # Get minimum in X Axis
        maxY = max([i[1] for i in nodePosList])

        for j in nodeEdSceneItems:
            if type(j) == QtWidgets.QGraphicsItem:
                j.setY(maxY)

    def verticalAlignCenterFn(self, event):
        nodeEdGraphView, nodeEdScene = self.getNodeEdUI()

        # Collect Items In Scene
        nodeEdSceneItems = nodeEdScene.selectedItems()

        nodePosList = []
        for i in nodeEdSceneItems:
            if type(i) == QtWidgets.QGraphicsItem:
                nodePosList.append([i.pos().x(), i.pos().y()])
        # Get minimum in X Axis
        minY = min([i[1] for i in nodePosList])
        maxY = max([i[1] for i in nodePosList])

        for j in nodeEdSceneItems:
            if type(j) == QtWidgets.QGraphicsItem:
                j.setY(((minY + maxY) / 2))
