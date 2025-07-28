from pywinauto.application import Application
import psutil
import asyncio
import threading
from waapi import WaapiClient, CannotConnectToWaapiException
from concurrent.futures import ThreadPoolExecutor, Future
from functools import wraps
import sys

# 确保Windows系统上的异步正确运行
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def async_threadsafe(func):
    """线程安全的异步执行装饰器，处理Future状态问题"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        
        # 创建一个新的Future用于跟踪结果
        result_future = loop.create_future()
        
        def submit_task():
            try:
                # 执行同步函数
                result = func(self, *args, **kwargs)
                # 确保在事件循环线程中设置结果
                loop.call_soon_threadsafe(result_future.set_result, result)
            except Exception as e:
                # 确保在事件循环线程中设置异常
                loop.call_soon_threadsafe(result_future.set_exception, e)
        
        # 提交任务到线程池
        self._executor.submit(submit_task)
        
        # 等待结果
        return await result_future
    
    return wrapper

class WwiseProfilerController:
    def __init__(self):
        # 线程安全机制
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Wwise连接属性
        self.pid = self.find_Wwise_window()
        self.app = None
        self.Wwise_window = None
        self.client = None
        self.connected = False
        
        # 初始化连接
        self.initialize_connection()

    @staticmethod
    def find_Wwise_window():
        """查找Wwise进程PID"""
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'Wwise.exe':
                return proc.pid
        return None

    def initialize_connection(self):
        """初始化Wwise连接"""
        if not self.pid:
            print('未找到Wwise.exe进程,请启动wwise后重新打开程序')
            return

        # 初始化窗口引用
        try:
            self.app = Application(backend="uia").connect(process=self.pid)
            self.Wwise_window = self.app.window()
            with self._lock:
                self.connected = True
            print('成功获取Wwise窗口引用')
        except Exception as e:
            print(f"获取Wwise窗口引用失败: {e}")
            self.Wwise_window = None
            
        # 尝试API连接
        try:
            self.client = WaapiClient()
            with self._lock:
                self.connected = True
            print('成功连接到Wwise API')
        except CannotConnectToWaapiException:
            print("Wwise API连接失败，将使用窗口操作")
        except Exception as e:
            print(f"Wwise API连接出错: {e}")


    @async_threadsafe
    def save_capture(self):
        """点击“Save Capture”控件"""
        if not self.Wwise_window:
            return "未连接到Wwise窗口，无法执行操作"

        try:
            # 定位“Save Capture”控件
            start_button = self.Wwise_window.child_window(
                title="S",
                control_type="Button"
            )
            start_button.click()
            return "已点击“Save Capture”控件"
        except Exception as e:
            return f"未能找到并点击Save控件，错误: {e}"

    @async_threadsafe
    def start_capture(self):
        """开始捕获"""
        if not self.connected:
            return "未连接到Wwise，请检查Wwise是否运行"
            
        return self.sync_start_capture()

    def sync_start_capture(self):
        """同步开始捕获操作"""
        try:
            if self.client:
                self.client.call("ak.wwise.core.profiler.startCapture")
                return "已通过API开始捕获"
            
            if self.Wwise_window:
                controls = [
                    self.Wwise_window.child_window(title="Start Capture", control_type="Button"),
                    self.Wwise_window.child_window(title="Start", control_type="Button")
                ]
                
                for control in controls:
                    if control.exists():
                        control.click()
                        return "已通过窗口控件开始捕获"
                
                self.Wwise_window.type_keys('^+c')
                return "已尝试通过快捷键开始捕获"
                
            return "无法执行开始捕获操作"
            
        except Exception as e:
            return f"开始捕获失败: {str(e)}"

    @async_threadsafe
    def stop_capture(self):
        """停止捕获"""
        if not self.connected:
            return "未连接到Wwise，请检查Wwise是否运行"
            
        return self.sync_stop_capture()

    def sync_stop_capture(self):
        """同步停止捕获操作"""
        try:
            if self.client:
                self.client.call("ak.wwise.core.profiler.stopCapture")
                return "已通过API停止捕获"
            
            if self.Wwise_window:
                controls = [
                    self.Wwise_window.child_window(title="Stop Capture", control_type="Button"),
                    self.Wwise_window.child_window(title="Stop", control_type="Button")
                ]
                
                for control in controls:
                    if control.exists():
                        control.click()
                        return "已通过窗口控件停止捕获"
                
                self.Wwise_window.type_keys('^+c')
                return "已尝试通过快捷键停止捕获"
                
            return "无法执行停止捕获操作"
            
        except Exception as e:
            return f"停止捕获失败: {str(e)}"

    def close(self):
        """清理资源"""
        if self._executor:
            self._executor.shutdown(wait=True)
        
        if self.client:
            try:
                # 额外添加WaapiClient的线程清理
                if hasattr(self.client, '_router') and hasattr(self.client._router, '_thread'):
                    self.client._router._thread.join(timeout=1.0)
                self.client.disconnect()
            except Exception as e:
                print(f"关闭Wwise连接时出错: {e}")


class OBSController:
    def __init__(self):
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="OBS")
        self.pid = self.find_obs_window()
        self.app = None
        self.obs_window = None
        
        if self.pid:
            try:
                self.app = Application(backend="uia").connect(process=self.pid)
                self.obs_window = self.app.window()
                with self._lock:
                    self.connected = True
                print('成功连接到OBS应用')
            except Exception as e:
                print(f"连接OBS失败: {e}")
        else:
            print('未找到obs64.exe进程,请启动obs后重新打开程序')

    @staticmethod
    def find_obs_window():
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'obs64.exe':
                return proc.pid
        return None

    async def async_operation(self, func):
        """改进的异步操作包装器，避免Future状态问题"""
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        def run_func():
            try:
                result = func()
                loop.call_soon_threadsafe(future.set_result, result)
            except Exception as e:
                loop.call_soon_threadsafe(future.set_exception, e)
        
        self._executor.submit(run_func)
        return await future

    async def recording_start(self):
        """开始录制（异步执行）"""
        def _sync_start():
            if not self.obs_window:
                return "未连接到OBS窗口"
                
            try:
                start_recording_button = self.obs_window.child_window(title="开始录制", control_type="CheckBox")
                start_recording_button.click()
                return "已点击“开始录制”按钮"
            except Exception as e:
                return f"未能找到并点击“开始录制”按钮，错误: {e}"
                
        return await self.async_operation(_sync_start)

    async def recording_stop(self):
        """停止录制（异步执行）"""
        def sync_stop():
            if not self.obs_window:
                return "未连接到OBS窗口"
                
            try:
                stop_recording_button = self.obs_window.child_window(title="停止录制", control_type="CheckBox")
                stop_recording_button.click()
                return "已点击“停止录制”按钮"
            except Exception as e:
                return f"未能找到并点击“停止录制”按钮，错误: {e}"
                
        return await self.async_operation(sync_stop)

    def close(self):
        """安全清理OBS资源"""
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
            print("OBS线程池已关闭")
        
        # 清除引用
        self.app = None
        self.obs_window = None


# 测试代码
# async def main():
#     # 测试Wwise控制器
#     print("=== 测试Wwise控制器 ===")
#     wwise = WwiseProfilerController()
    
#     # 等待Wwise连接建立
#     await asyncio.sleep(1)
    
#     if wwise.connected:
#         print("开始捕获测试...")
#         result = await wwise.start_capture()
#         print(result)
        
#         await asyncio.sleep(2)
        
#         print("停止捕获测试...")
#         result = await wwise.stop_capture()
#         print(result)
        
#         await asyncio.sleep(2)
        
#         print("保存捕获测试...")
#         result = await wwise.save_capture()
#         print(result)
#     else:
#         print("Wwise连接失败，无法测试")
    
#     # 测试OBS控制器
#     print("\n=== 测试OBS控制器 ===")
#     obs = OBSController()
#     if obs.pid:
#         print("开始录制测试...")
#         result = await obs.recording_start()
#         print(result)
        
#         await asyncio.sleep(2)
        
#         print("停止录制测试...")
#         result = await obs.recording_stop()
#         print(result)
#     else:
#         print("OBS连接失败，无法测试")
    
#     # 清理资源
#     await asyncio.sleep(1)  # 给操作完成留出时间
#     wwise.close()
#     obs.close()
#     print("\n所有测试完成，资源已清理")

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except Exception as e:
#         print(f"程序执行出错: {e}")
    
