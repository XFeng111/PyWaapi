import sys
import io

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QStandardItem
from PyQt6.QtCore import QObject, pyqtSignal

from Record import WwiseProfilerController, OBSController
from Ui_WindowShow import Ui_ReaWwise_Tool
from ReaAction import ReaAction


# 输出打印消息到 ListView
# 输出重定向类：捕获print内容并通过信号发送
class PrintRedirector(io.StringIO):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal  # 用于传递输出内容的信号

    def write(self, text):
        super().write(text)  # 保留原始输出功能
        if text.strip():  # 过滤空行
            self.signal.emit(text.strip())  # 发送非空内容到UI

    def flush(self):
        super().flush()


# 信号中转类（用于跨线程安全更新UI）
class SignalEmitter(QObject): 
    print_signal = pyqtSignal(str)  # 传递print内容的信号



class ReaWwise_Tool(QtWidgets.QMainWindow, Ui_ReaWwise_Tool):
    def __init__(self):
        super(ReaWwise_Tool, self).__init__()
        self.setupUi(self)
        
        # 初始化列表模型
        self.model = QtGui.QStandardItemModel()
        # 绑定listview
        self.listView.setModel(self.model)

        # 初始化信号发射器和输出重定向
        self.signal_emitter = SignalEmitter()
        self.signal_emitter.print_signal.connect(self.add_log)  # 绑定信号到日志更新函数
        self.redirector = PrintRedirector(self.signal_emitter.print_signal)
        sys.stdout = self.redirector  # 重定向stdout到自定义输出流

        # 初始化类
        self.wwise = WwiseProfilerController()
        self.obs = OBSController()
        self.rp = ReaAction()

    # --------------------------------------------------------------------
        # 绑定按钮 录制，结束，Save Log
        self.RecordingStart.clicked.connect(self.StartCapture)
        self.RecordingStop.clicked.connect(self.StopCapture)
        self.SaveLog.clicked.connect(self.wwise.save_capture)
        
        # 绑定按钮 连接Capture，播放，停止
        self.LinkCapture.stateChanged.connect(self.link_capture)
        self.Start.clicked.connect(self.rp.Start)
        self.Stop.clicked.connect(self.rp.Stop)

        # 绑定按钮  WwhispeAssistant，导入视频，CaptureLog.txt
        self.WwhispeAssistant.clicked.connect(self.rp.WwhispeAssistant)
        self.InsertMedia.clicked.connect(self.rp.InsertMedia)
        self.InputLog.clicked.connect(self.input_log)

        # 绑定按钮 转到上一个标记，转到下一个标记
        self.PreviouMarker.clicked.connect(self.rp.PreviouMarker)
        self.NextMarker.clicked.connect(self.rp.NextMarker)

        # 绑定按钮 清空
        self.Clear.clicked.connect(self.clear_Log)

    # ---------------------------------------------------------------------
    # 定义按钮函数
    def StartCapture(self):
        self.wwise.start_capture()
        self.obs.recording_start()

    def StopCapture(self):
        self.wwise.stop_capture()
        self.obs.recording_stop()

    def link_capture(self, state):
        """复选框状态变化时触发：勾选时启动捕获，取消勾选时停止捕获"""
        if state == 2:  # Qt.CheckState.Checked == 2
            self.wwise.start_capture()
            print("已连接Capture")
        else:  # 未勾选状态
            self.wwise.stop_capture()
            print("已断开Capture")

    def input_log(self):
        self.rp.InputLog()
        self.rp.rename_camera_tracks_to_listener()

    def clear_Log(self):
        self.model.clear()

    def add_log(self, text):
        """向listView添加日志内容"""
        item = QStandardItem(text)
        self.model.appendRow(item)
        self.listView.scrollToBottom()  # 自动滚动到底部


# 主程序执行---------------------------------------------------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ReaWwise_Tool()
    ex.show()
    sys.exit(app.exec())

