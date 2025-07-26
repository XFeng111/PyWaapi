import reapy  # 外部控制需用 reapy 库


class ReaAction:
    def trigger_custom_script_by_guid(guid):
        """
        调用：传入自定义脚本
        例如：trigger_custom_script_by_guid("_RSde44f60973f53a2a211f87e97990c5c2cf69590b")
        """
        try:
            reapy.connect()  # 连接到本地 Reaper（需开启网络控制）

            action_id = reapy.get_command_id(guid) #获取id
            reapy.perform_action(action_id)  # 输入id
            print(f"已触发脚本（GUID: {guid}）")
            
        except Exception as e:
            print(f"执行失败: {e}")


    """

    脚本: kusa_Wwhisper Assistant.lua "_RSde44f60973f53a2a211f87e97990c5c2cf69590b"   
    脚本: kusa_Wwhisper.lua "_RSc32ceb513fe80bdbf78b7b6be9bb00453b6c6516"

    插入媒体文件... ⇌ Insert media files... 40018
    走带: 停止 ⇌ Transport: Stop 1016

    标记: 转到上一个标记/工程开始 ⇌ Markers: Go to previous marker/project start 40172
    标记: 转到下一个标记/工程结束 ⇌ Markers: Go to next marker/project end 40173

    脚本: 一键导入CaptureLog.lua "_RSf46dc4e7683b6e8057a688b3720fe4d6891bbb64"

    """

    # 指定Listener
    def rename_camera_tracks_to_listener():
        """
        将当前工程，轨道名称含camera的名称修改为Listener
        """
        try:
            # 连接到正在运行的Reaper（需开启网络控制）
            reapy.connect()
            print("已成功连接到Reaper工程")

            # 获取当前工程的所有轨道
            project = reapy.Project()  # 获取当前激活的工程
            tracks = project.tracks    # 所有轨道的列表（按顺序排列）

            if not tracks:
                print("当前工程中没有轨道")
                return

            # 遍历轨道，检查并修改名称
            renamed_count = 0
            for track in tracks:
                current_name = track.name  # 获取轨道当前名称
                # 检查名称是否包含"Camera"（不区分大小写）
                if "camera" in current_name.lower():
                    # 修改轨道名称为"Listener"
                    track.name = "Listener"
                    print(f'已修改轨道："{current_name}" → "Listener"')
                    renamed_count += 1

            # 输出结果总结
            if renamed_count > 0:
                print(f"\n操作完成，共修改了 {renamed_count} 个轨道")
            else:
                print("\n未找到名称含'Camera'的轨道")

        except Exception as e:
            print(f"执行失败：{e}")

    # 脚本: kusa_Wwhisper Assistant.lua "_RSde44f60973f53a2a211f87e97990c5c2cf69590b"   
    def WwhispeAssistant():
        ReaAction.trigger_custom_script_by_guid("_RSde44f60973f53a2a211f87e97990c5c2cf69590b")

    # 脚本: kusa_Wwhisper.lua "_RSc32ceb513fe80bdbf78b7b6be9bb00453b6c6516"
    def Start():
        ReaAction.trigger_custom_script_by_guid("_RSc32ceb513fe80bdbf78b7b6be9bb00453b6c6516")

    # 插入媒体文件... ⇌ Insert media files... 40018
    def InsertMedia():
        ReaAction.trigger_custom_script_by_guid(40018)

    # 走带: 停止 ⇌ Transport: Stop 1016
    def Stop():
        ReaAction.trigger_custom_script_by_guid(1016)

    # 标记: 转到上一个标记/工程开始 ⇌ Markers: Go to previous marker/project start 40172
    def PreviouMarker():
        ReaAction.trigger_custom_script_by_guid(40172)

    # 标记: 转到下一个标记/工程结束 ⇌ Markers: Go to next marker/project end 40173    
    def NextMarker():
        ReaAction.trigger_custom_script_by_guid(40173)

    # 脚本: 一键导入CaptureLog.lua "_RSf46dc4e7683b6e8057a688b3720fe4d6891bbb64"
    def InputLog():
        ReaAction.trigger_custom_script_by_guid("_RSf46dc4e7683b6e8057a688b3720fe4d6891bbb64")

        
