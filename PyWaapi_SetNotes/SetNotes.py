from waapi import WaapiClient
import sys
import socket
from io import StringIO
import contextlib

def collect_output(func):
    """装饰器函数：捕获被装饰函数中的所有print输出，返回输出内容列表"""
    def wrapper(*args, **kwargs):
        output_buffer = StringIO()  # 创建字符串缓冲区，用于捕获输出
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
            # 执行被装饰的函数，所有print和错误输出都会被捕获
            func(*args, **kwargs)
        
        # 获取缓冲区内容并按行分割，过滤空行
        output_content = output_buffer.getvalue().strip().split('\n')
        return [line.strip() for line in output_content if line.strip()]
    
    return wrapper

@collect_output
def batch_add_custom_notes(notes_content):
    try:
        """让用户输入备注内容，为选中对象批量添加（支持外部传入内容）"""
        # # 优先使用外部传入的内容，否则让用户输入
        # if notes_content is None:
        #     print("请输入需要批量添加的备注内容（输入完成后按回车）：")
        #     notes_content = input("> ").strip()  # 获取用户输入并去除首尾空格
        #     print(f"添加备注:{notes_content}")

        # if not notes_content:
        #     print("⚠️ 备注内容不能为空，请重新运行脚本并输入内容")
        #     return
        
        """为选中对象批量添加备注（仅处理传入的内容，不进行交互式输入）"""
        print(f"准备添加备注: {notes_content}")

        # 连接 Wwise 的 WAAPI 服务（默认端口 8080）
        with WaapiClient() as client:
            print("✅ 成功连接到 Wwise WAAPI 服务")

            # 1. 获取当前选中的对象（通过 WAAPI 调用 ak.wwise.ui.getSelectedObjects）
            result = client.call(
                "ak.wwise.ui.getSelectedObjects",
                {
                    "options": {
                        "return": ["id", "name", "type"]  # 只返回对象的 ID、名称、类型
                    }
                }
            )

            # 提取选中的对象列表
            selected_objects = result.get("objects", [])
            if not selected_objects:
                print("⚠️ 未选中任何对象，请在 Wwise 中先选择需要添加备注的对象")
                return

            print(f"\n📌 共选中 {len(selected_objects)} 个对象，开始批量添加 Notes...")

            # 2. 遍历选中对象，使用 setNotes 接口设置备注
            success_count = 0
            fail_count = 0
            fail_details = []

            for obj in selected_objects:
                obj_id = obj["id"]
                obj_name = obj["name"]
                obj_type = obj["type"]

                try:
                    # 调用 ak.wwise.core.object.setNotes 接口
                    client.call(
                        "ak.wwise.core.object.setNotes",
                        {
                            "object": obj_id,  # 对象的 GUID 或路径
                            "value": notes_content  # 要设置的备注内容
                        }
                    )
                    success_count += 1
                    print(f"✅ 成功：[{obj_type}] {obj_name} 备注：{notes_content}")
                except Exception as e:
                    fail_count += 1
                    fail_details.append(f"❌ 失败：[{obj_type}] {obj_name}（错误：{str(e)}）")

            # 输出统计结果
            print(f"\n📊 操作完成：成功 {success_count} 个，失败 {fail_count} 个")
            if fail_details:
                print("\n❌ 失败详情：")
                for detail in fail_details:
                    print(detail)

    except (ConnectionRefusedError, socket.error) as e:
        print("❌ 无法连接到 Wwise WAAPI 服务，请确保：")
        print("1. Wwise 已启动")
        print("2. WAAPI 服务已开启（在 Wwise 设置中确认）")
        print("3. 端口未被占用（默认端口 8080）")
    except Exception as e:
        print(f"❌ 发生错误：{str(e)}")


if __name__ == "__main__":
    print("===== Wwise 批量添加备注工具 =====")
    # 调用函数并获取所有输出内容
    output_lines = batch_add_custom_notes()
    
    # 演示：打印收集到的输出（实际使用时可根据需求处理）
    print("\n===== 收集到的输出内容 =====")
    for line in output_lines:
        print(line)
    
    input("\n按回车键退出...")
