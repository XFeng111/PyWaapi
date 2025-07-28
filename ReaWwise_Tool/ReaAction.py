import reapy
import asyncio
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import threading
import time

# 创建线程池复用资源
executor = ThreadPoolExecutor(max_workers=20)
_executor_shutdown = False  # 线程池关闭标记
# 线程锁确保连接操作线程安全
connection_lock = threading.Lock()

def async_reapy(func):
    """装饰器：将reapy同步操作转为异步"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        try:
            # 使用线程池的超时机制替代reapy.connect的timeout参数
            return await asyncio.wait_for(
                loop.run_in_executor(executor, func, *args, **kwargs),
                timeout=30.0  # 5秒超时
            )
        except TimeoutError:
            return "操作超时，请检查Reaper是否响应"
        except Exception as e:
            return f"操作失败: {str(e)}"
    return wrapper

def shutdown_executor():
    """确保线程池被正确关闭"""
    global _executor_shutdown
    if not _executor_shutdown:
        executor.shutdown(wait=True, cancel_futures=True)
        _executor_shutdown = True
        print("ReaAction线程池已关闭")

class Rea_Action:
    _reapy_connected = False  # 连接状态缓存
    _connection_attempted = False  # 避免重复尝试连接

    @staticmethod
    def _ensure_connection():
        """确保reapy连接已建立，带重试机制"""
        if Rea_Action._reapy_connected:
            return True
            
        with connection_lock:
            # 双重检查锁定模式
            if Rea_Action._reapy_connected:
                return True
                
            # 避免重复尝试连接
            if Rea_Action._connection_attempted:
                raise ConnectionError("之前的Reaper连接尝试已失败，请检查Reaper是否运行")

            try:
                # 最多尝试3次连接，移除不支持的timeout参数
                for attempt in range(3):
                    try:
                        reapy.connect()  # 修复：移除不支持的timeout参数
                        Rea_Action._reapy_connected = True
                        print("已连接到Reaper")
                        return True
                    except:
                        if attempt < 2:
                            time.sleep(1)  # 重试前等待1秒
                            continue
                        raise
            except Exception as e:
                Rea_Action._connection_attempted = True  # 标记连接尝试失败
                raise ConnectionError(f"Reaper连接失败: {e}")


    @staticmethod
    @async_reapy
    def trigger_custom_script_by_guid(guid):
        """异步触发自定义脚本"""
        try:
            if not Rea_Action._ensure_connection():
                return "无法连接到Reaper"
                
            # 验证GUID格式
            if isinstance(guid, str):
                if not (guid.startswith("_RS") or guid.startswith("__")):
                    return f"无效的GUID格式: {guid}"
            
            action_id = reapy.get_command_id(guid)
            reapy.perform_action(action_id)
            return f"已触发脚本（GUID: {guid}）"
        except Exception as e:
            return f"执行失败: {e}"

    @staticmethod
    async def rename_camera_tracks_to_listener():
        """异步重命名含camera的轨道"""
        try:
            Rea_Action._ensure_connection()
            project = reapy.Project()
            tracks = project.tracks

            if not tracks:
                return "当前工程中没有轨道"

            renamed_count = 0
            for track in tracks:
                current_name = track.name
                if "camera" in current_name.lower():
                    track.name = "Listener"
                    renamed_count += 1
                    print(f'已修改轨道："{current_name}" → "Listener"')

            return f"\n操作完成，共修改了 {renamed_count} 个轨道" if renamed_count else "\n未找到名称含'Camera'的轨道"
        except Exception as e:
            return f"执行失败：{e}"

    # 异步接口方法
    @staticmethod
    async def WwhispeAssistant():
        """
        脚本: kusa_Wwhisper Assistant.lua
        _RSde44f60973f53a2a211f87e97990c5c2cf69590b
        """
        result = await Rea_Action.trigger_custom_script_by_guid(
            "_RSde44f60973f53a2a211f87e97990c5c2cf69590b", "WwhispeAssistant"
        )
        print(result)

    @staticmethod
    async def Start():
        """
        脚本: kusa_Wwhisper.lua
        _RSc32ceb513fe80bdbf78b7b6be9bb00453b6c6516
        """
        result = await Rea_Action.trigger_custom_script_by_guid(
            "_RSc32ceb513fe80bdbf78b7b6be9bb00453b6c6516", "播放"
        )
        print(result)

    @staticmethod
    async def InsertMedia():
        """
        插入媒体文件... ⇌ Insert media files...
        40018
        """
        result = await Rea_Action.trigger_custom_script_by_guid(40018, "导入视频")
        print(result)

    @staticmethod
    async def Stop():
        """
        走带: 停止 ⇌ Transport: Stop
        1016
        """
        result = await Rea_Action.trigger_custom_script_by_guid(1016, "停止")
        print(result)

    @staticmethod
    async def PreviouMarker():
        """
        标记: 转到上一个标记/工程开始 ⇌ Markers: Go to previous marker/project start
        40172
        """
        result = await Rea_Action.trigger_custom_script_by_guid(40172, "转到上一个标记")
        print(result)

    @staticmethod
    async def NextMarker():
        """
        标记: 转到下一个标记/工程结束 ⇌ Markers: Go to next marker/project end
        40173
        """
        result = await Rea_Action.trigger_custom_script_by_guid(40173, "转到下一个标记")
        print(result)

    @staticmethod
    async def InputLog():
        """
        脚本: 一键导入CaptureLog.lua
        _RS40adae0a80e5768382a400485b2eead586038b35

        def rename_camera_tracks_to_listener() 重命名listener
        """
        result = await Rea_Action.trigger_custom_script_by_guid(
            "_RS40adae0a80e5768382a400485b2eead586038b35", "CaptureLog.txt"
        )
        rename_result = await Rea_Action.rename_camera_tracks_to_listener()
        print(result)
        print(rename_result)
        
        

# 测试功能
# if __name__ == "__main__":
#     # 创建实例
#     rp = Rea_Action()
    
#     # 定义异步调用函数（不需要self参数，因为这里不是类方法）
#     async def handle():
#         # 直接使用rp实例调用，不需要self 
#         await rp.InputLog()
    
#     # 使用asyncio.run()运行异步函数
#     asyncio.run(handle())
