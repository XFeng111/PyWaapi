import sys
import io
import asyncio
import threading

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QStandardItem
from PyQt6.QtCore import QObject, pyqtSignal

from Record import WwiseProfilerController, OBSController
from Ui_WindowShow import Ui_ReaWwise_Tool
from ReaAction import Rea_Action, executor as rea_executor


# 输出重定向类：捕获print内容
class PrintRedirector(io.StringIO):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def write(self, text):
        super().write(text)
        if text.strip():
            self.signal.emit(text.strip())

    def flush(self):
        super().flush()


# 信号中转类（跨线程安全更新UI）
class SignalEmitter(QObject):
    print_signal = pyqtSignal(str)

# -------------------------------------------------------------------------------

class ReaWwise_Tool(QtWidgets.QMainWindow, Ui_ReaWwise_Tool):
    def __init__(self):
        super(ReaWwise_Tool, self).__init__()
        self.setupUi(self)
        
        # 初始化列表模型
        self.model = QtGui.QStandardItemModel()
        self.listView.setModel(self.model)

        # 初始化信号和输出重定向
        self.signal_emitter = SignalEmitter()
        self.signal_emitter.print_signal.connect(self.add_log)
        self.redirector = PrintRedirector(self.signal_emitter.print_signal)
        self.original_stdout = sys.stdout  # 保存原始stdout
        sys.stdout = self.redirector

        # 初始化控制器
        self.wwise = WwiseProfilerController()
        self.obs = OBSController()
        self.rp = Rea_Action()  

        # 线程和任务跟踪
        self.threads = []  # 跟踪所有创建的线程
        self.running_tasks = set()  # 跟踪异步任务

        # 绑定按钮事件
        self._bind_buttons()

# -------------------------------------------------------------------------------

    def _bind_buttons(self):
        """绑定所有按钮事件（异步执行）"""
        # 录制控制
        self.RecordingStart.clicked.connect(self._run_async(self.StartCapture))
        self.RecordingStop.clicked.connect(self._run_async(self.StopCapture))
        self.SaveLog.clicked.connect(self._run_async(self.wwise.save_capture))
        
        # 播放控制
        self.LinkCapture.stateChanged.connect(self.link_capture)
        self.Start.clicked.connect(self._run_async(self.rp.Start))
        self.Stop.clicked.connect(self._run_async(self.rp.Stop))

        # 其他操作
        self.WwhispeAssistant.clicked.connect(self._run_async(self.rp.WwhispeAssistant))
        self.InsertMedia.clicked.connect(self._run_async(self.rp.InsertMedia))
        self.InputLog.clicked.connect(self._run_async(self.rp.InputLog))
        self.PreviouMarker.clicked.connect(self._run_async(self.rp.PreviouMarker))
        self.NextMarker.clicked.connect(self._run_async(self.rp.NextMarker))
        self.Clear.clicked.connect(self.clear_Log)
        # self.Reconnect.clicked.connect(self.reconnect_all)

# -------------------------------------------------------------------------------

    def _run_async(self, coro):
        """修复线程只能启动一次的问题，每次调用创建新线程"""
        def wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                task = loop.create_task(coro())
                self.running_tasks.add(task)
                
                def task_done(fut):
                    self.running_tasks.discard(fut)
                
                task.add_done_callback(task_done)
                loop.run_until_complete(task)
            finally:
                loop.close()
        
        # 关键修改：每次调用返回新线程的启动逻辑，而非固定线程
        def thread_starter():
            thread = threading.Thread(target=wrapper, daemon=True)
            self.threads.append(thread)
            thread.start()
        
        return thread_starter  # 返回创建并启动新线程的函数

    # 核心业务逻辑
    async def StartCapture(self):
        wwise_result = await self.wwise.start_capture()
        obs_result = await self.obs.recording_start()
        if wwise_result:
            print(wwise_result)
        if obs_result:
            print(obs_result)

    async def StopCapture(self):
        wwise_result = await self.wwise.stop_capture()
        obs_result = await self.obs.recording_stop()
        if wwise_result:
            print(wwise_result)
        if obs_result:
            print(obs_result)

    def link_capture(self, state):
        """Capture联动（同步操作，内部调用异步方法）"""
        async def _link():
            if state == 2:
                result = await self.wwise.start_capture()
                print(result or "已连接Capture")
            else:
                result = await self.wwise.stop_capture()
                print(result or "已断开Capture")
        self._run_async(_link)()

    def clear_Log(self):
        self.model.clear()

        # 清理异步任务
        self._cleanup_async_tasks()

    def add_log(self, text):
        """添加日志到ListView"""
        item = QStandardItem(text)
        self.model.appendRow(item)
        self.listView.scrollToBottom()

    # def reconnect_all(self):
    #     self.wwise.find_Wwise_window()
    #     self.wwise.initialize_connection()

    #     self.obs.find_obs_window()
    #     self.rp.ensure_connection()


    # -------------------------------------------------------------------------------
    # 资源清理与程序退出处理
    # -------------------------------------------------------------------------------

    def closeEvent(self, event: QtGui.QCloseEvent):
        """窗口关闭时清理所有资源"""
        self.add_log("开始清理资源，准备退出程序...")
        
        # 1. 清理异步任务
        self._cleanup_async_tasks()
        
        # 2. 停止所有控制器
        self._stop_controllers()
        
        # 3. 关闭所有线程池
        self._shutdown_all_executors()
        
        # 4. 等待线程结束
        self._join_threads(timeout=2.0)
        
        # 5. 恢复标准输出
        sys.stdout = self.original_stdout
        
        # 6. 打印退出信息
        print("程序已正常退出")
        
        # 接受关闭事件
        event.accept()

    def _stop_controllers(self):
        """停止所有控制器并释放资源，调整关闭顺序"""
        # 首先处理Wwise控制器，确保Waapi线程优先关闭
        if hasattr(self, 'wwise'):
            # 先停止捕获
            if hasattr(self.wwise, 'stop_capture'):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.wwise.stop_capture())
                    loop.close()
                except Exception as e:
                    self.add_log(f"停止Wwise捕获时出错: {e}")
            
            # 再关闭控制器
            if hasattr(self.wwise, 'close'):
                self.wwise.close()

        # 处理OBS控制器
        if hasattr(self, 'obs'):
            if hasattr(self.obs, 'recording_stop'):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.obs.recording_stop())
                    loop.close()
                except Exception as e:
                    self.add_log(f"停止OBS录制时出错: {e}")
            
            if hasattr(self.obs, 'close'):
                self.obs.close()

        # 处理ReaAction
        if hasattr(self, 'rp') and hasattr(self.rp, 'Stop'):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.rp.Stop())
                loop.close()
            except Exception as e:
                self.add_log(f"停止ReaAction时出错: {e}")

    # 修改_cleanup_async_tasks方法，处理Waapi相关任务
    def _cleanup_async_tasks(self):
        """清理所有运行中的异步任务，包括Waapi相关任务"""
        if not self.running_tasks:
            return
            
        self.add_log(f"正在终止 {len(self.running_tasks)} 个异步任务...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def cancel_tasks():
            for task in self.running_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        # 增加超时处理，避免无限等待
                        await asyncio.wait_for(task, timeout=1.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError, RuntimeError):
                        pass  # 忽略取消、超时和运行时错误
        
        try:
            loop.run_until_complete(cancel_tasks())
        finally:
            loop.close()
        self.running_tasks.clear()

    def _shutdown_all_executors(self):
        """关闭所有线程池"""
        # 关闭ReaAction的全局线程池
        rea_executor.shutdown(wait=True, cancel_futures=True)
        
        # 关闭Wwise控制器的线程池
        if hasattr(self.wwise, '_executor'):
            self.wwise._executor.shutdown(wait=True, cancel_futures=True)
        
        # 关闭OBS控制器的线程池
        if hasattr(self.obs, '_executor'):
            self.obs._executor.shutdown(wait=True, cancel_futures=True)

    def _join_threads(self, timeout):
        """等待线程结束，超时则强制标记为daemon"""
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout)
                if thread.is_alive():
                    thread.daemon = True  # 确保随主线程退出
        self.threads.clear()

# -------------------------------------------------------------------------------

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ReaWwise_Tool()
    ex.show()
    sys.exit(app.exec())
