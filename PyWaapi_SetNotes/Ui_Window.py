from PyQt6 import QtCore, QtGui, QtWidgets
import sys
from PyQt6.QtCore import Qt

class Ui_Wwise_SetNotes(object):
    def setupUi(self, Wwise_SetNotes):
        Wwise_SetNotes.setObjectName("Wwise_SetNotes")
        Wwise_SetNotes.resize(831, 300)
        self.lineEdit = QtWidgets.QLineEdit(parent=Wwise_SetNotes)
        self.lineEdit.setGeometry(QtCore.QRect(20, 20, 601, 31))
        self.lineEdit.setObjectName("lineEdit")
        self.pushButton = QtWidgets.QPushButton(parent=Wwise_SetNotes)
        self.pushButton.setGeometry(QtCore.QRect(740, 20, 71, 31))
        self.pushButton.setObjectName("pushButton")
        self.pushButton_2 = QtWidgets.QPushButton(parent=Wwise_SetNotes)
        self.pushButton_2.setGeometry(QtCore.QRect(640, 20, 71, 31))
        self.pushButton_2.setObjectName("pushButton_2")
        self.listView = QtWidgets.QListView(parent=Wwise_SetNotes)
        self.listView.setGeometry(QtCore.QRect(20, 71, 791, 201))
        self.listView.setObjectName("listView")
        # 设置列表视图不可编辑
        self.listView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        self.retranslateUi(Wwise_SetNotes)
        QtCore.QMetaObject.connectSlotsByName(Wwise_SetNotes)

    def retranslateUi(self, Wwise_SetNotes):
        _translate = QtCore.QCoreApplication.translate
        Wwise_SetNotes.setWindowTitle(_translate("Wwise_SetNotes", "Wwise_SetNotes"))
        self.pushButton.setText(_translate("Wwise_SetNotes", "批量Notes"))
        self.pushButton_2.setText(_translate("Wwise_SetNotes", "清空"))

