from .Qt.QtWidgets import QDialog
from .Qt.QtCompat import loadUi
from .utils import getUiFile
from .alignNodesLib import align, spread, distribute, getSelItems, xSetter, ySetter


class AlignNodesDialog(QDialog):
    def __init__(self, parent=None):
        super(AlignNodesDialog, self).__init__(parent)
        loadUi(getUiFile(__file__), self)

        self.uiHorLeftBTN.clicked.connect(self.horLeft)
        self.uiHorCenterBTN.clicked.connect(self.horCenter)
        self.uiHorRightBTN.clicked.connect(self.horRight)
        self.uiHorSpreadBTN.clicked.connect(self.horSpread)
        self.uiHorDistLeftBTN.clicked.connect(self.horDistributeLeft)
        self.uiHorDistCenterBTN.clicked.connect(self.horDistributeCenter)
        self.uiHorDistRightBTN.clicked.connect(self.horDistributeRight)

        self.uiVerTopBTN.clicked.connect(self.verTop)
        self.uiVerCenterBTN.clicked.connect(self.verCenter)
        self.uiVerBottomBTN.clicked.connect(self.verBottom)
        self.uiVerSpreadBTN.clicked.connect(self.verSpread)
        self.uiVerDistTopBTN.clicked.connect(self.verDistributeTop)
        self.uiVerDistCenterBTN.clicked.connect(self.verDistributeCenter)
        self.uiVerDistBottomBTN.clicked.connect(self.verDistributeBottom)

    def horLeft(self):
        align(getSelItems(), xSetter, 0.0)

    def horCenter(self):
        align(getSelItems(), xSetter, 0.5)

    def horRight(self):
        align(getSelItems(), xSetter, 1.0)

    def horSpread(self):
        spread(getSelItems(), xSetter)

    def horDistributeLeft(self):
        distribute(getSelItems(), xSetter, 0.0)

    def horDistributeCenter(self):
        distribute(getSelItems(), xSetter, 0.5)

    def horDistributeRight(self):
        distribute(getSelItems(), xSetter, 1.0)

    def verTop(self):
        align(getSelItems(), ySetter, 0.0)

    def verCenter(self):
        align(getSelItems(), ySetter, 0.5)

    def verBottom(self):
        align(getSelItems(), ySetter, 1.0)

    def verSpread(self):
        spread(getSelItems(), ySetter)

    def verDistributeTop(self):
        distribute(getSelItems(), ySetter, 0.0)

    def verDistributeCenter(self):
        distribute(getSelItems(), ySetter, 0.5)

    def verDistributeBottom(self):
        distribute(getSelItems(), ySetter, 1.0)
