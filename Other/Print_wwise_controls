import psutil
from pywinauto import Application

def print_wwise_controls():
    # 查找 Wwise 进程
    wwise_pid = None
    for proc in psutil.process_iter(['name', 'pid']):
        if proc.info['name'] == 'Wwise.exe':
            wwise_pid = proc.info['pid']
            break
    if not wwise_pid:
        print("未找到运行中的 Wwise.exe 进程")
        return

    try:
        # 连接 Wwise 并获取主窗口
        app = Application(backend="uia").connect(process=wwise_pid)
        main_window = app.window()  # 获取主窗口

        print("===== Wwise 窗口控件列表 =====")
        # 打印所有控件标识（内置方法，兼容性更好）
        main_window.print_control_identifiers(depth=5)  # depth 控制遍历深度

    except Exception as e:
        print(f"操作失败: {e}")

if __name__ == "__main__":
    print_wwise_controls()
