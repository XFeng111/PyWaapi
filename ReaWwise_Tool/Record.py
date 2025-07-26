from pywinauto.application import Application
import psutil
from waapi import WaapiClient, CannotConnectToWaapiException


class OBSController:
    def __init__(self):
        self.pid = self.find_obs_window()
        if self.pid:
            self.app = Application(backend="uia").connect(process=self.pid)
            self.obs_window = self.app.window()
            print('成功连接到OBS应用')
        else:
            print('未找到obs64.exe进程,请启动obs后重新打开程序')

    @staticmethod
    def find_obs_window():
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'obs64.exe':
                return proc.pid
        return None

    def recording_start(self):
        if self.pid:
            try:
                start_recording_button = self.obs_window.child_window(title="开始录制", control_type="CheckBox")
                start_recording_button.click()
                print("已点击“开始录制”按钮")
            except Exception as e:
                print(f"未能找到并点击“开始录制”按钮，错误: {e}")

    def recording_stop(self):
        if self.pid:
            try:
                stop_recording_button = self.obs_window.child_window(title="停止录制", control_type="CheckBox")
                stop_recording_button.click()
                print("已点击“停止录制”按钮")
            except Exception as e:
                print(f"未能找到并点击“停止录制”按钮，错误: {e}")


class WwiseProfilerController:
    def __init__(self):
        # 初始化时连接Wwise
        self.pid = self.find_Wwise_window()
        self.app = None
        self.Wwise_window = None
        self.client = None
        if self.pid:
            try:
                self.app = Application(backend="uia").connect(process=self.pid)
                self.Wwise_window = self.app.window()
                print('成功连接到Wwise应用')
            except Exception as e:
                print(f"连接Wwise失败: {e}")
        else:
            print('未找到Wwise.exe进程,请启动wwise后重新打开程序')

    def start_capture(self):
        try:
            if not self.client:
                self.client = WaapiClient()
            self.client.call("ak.wwise.core.profiler.startCapture")
        except CannotConnectToWaapiException:
            print("无法连接到Waapi：Wwise是否正在运行且Wwise创作API已启用？")

    def stop_capture(self):
            try:
                if not self.client:
                    self.client = WaapiClient()
                self.client.call("ak.wwise.core.profiler.stopCapture")
            except CannotConnectToWaapiException:
                print("无法连接到Waapi：Wwise是否正在运行且Wwise创作API已启用？")
            

    @staticmethod
    def find_Wwise_window():
        """查找Wwise进程PID"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'Wwise.exe':
                return proc.pid
        return None

    def save_capture(self):
        """点击“Save Capture”控件（开始捕获）"""
        if not self.Wwise_window:
            print("未连接到Wwise窗口，无法执行操作")
            return

        try:
            # 定位“Save Capture”控件（根据实际控件属性调整）
            start_button = self.Wwise_window.child_window(
                title="S",
                control_type="Button"
            )
            start_button.click()
            print("已点击“Save Capture”控件")
        except Exception as e:
            print(f"未能找到并点击Save控件，错误: {e}")




