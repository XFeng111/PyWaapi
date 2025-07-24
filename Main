from PyQt6 import QtCore, QtGui, QtWidgets
import sys
import SetNotes  # 导入SetNotes.py模块
from SetNotes import batch_add_custom_notes
import Ui_Window # 导入Ui_Window.py模块
from Ui_Window import Ui_Wwise_SetNotes

class MainWindow(QtWidgets.QMainWindow, Ui_Wwise_SetNotes):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 初始化列表模型
        self.model = QtGui.QStandardItemModel()
        self.listView.setModel(self.model)
        # 绑定按钮事件
        self.pushButton.clicked.connect(self.batch_add_custom_notes)
        self.pushButton_2.clicked.connect(self.reset_all)

    def Note(self):
        """获取lineEdit中的输入内容"""
        return self.lineEdit.text().strip()  # 返回输入框内容（去除首尾空格）

    def reset_all(self):
        """重置输入框和列表视图"""
        self.lineEdit.clear()
        self.model.clear()

    def add_log(self, text, is_error=False):
        """向列表视图添加日志信息"""
        item = QtGui.QStandardItem(text)
        # 错误信息显示为红色
        if is_error:
            item.setForeground(QtGui.QColor(255, 0, 0))
        self.model.appendRow(item)
        # 自动滚动到底部
        self.listView.scrollToBottom()

    def batch_add_custom_notes(self):
        """调用SetNotes中的批量添加函数，并显示结果"""
        # 清空之前的日志
        self.model.clear()
        # 获取输入内容
        notes_content = self.Note()
        # 调用SetNotes中的函数并获取输出
        try:
            # 调用带装饰器的函数，获取所有输出行
            output_lines = SetNotes.batch_add_custom_notes(notes_content=notes_content)
            # 显示输出结果
            for line in output_lines:
                # 判断是否为错误信息（包含特定标记）
                is_error = "⚠️" in line or "❌" in line
                self.add_log(line, is_error)
        except Exception as e:
            self.add_log(f"调用函数失败：{str(e)}", is_error=True)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
