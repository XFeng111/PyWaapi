from waapi import WaapiClient, CannotConnectToWaapiException
from pprint import pprint
import msvcrt
from WAAPI_Functions import Core_object, Core_undo, Ui


def get_children(c_obj, object_id):
    """
    获取对象的直接子集列表，每项包含 id / name / type。
    WAAPI 点号语法返回并行列表，此处统一转为 dict 列表。
    """
    res = c_obj.object_get(object_id, ["children.id", "children.name", "children.type"])
    ret = res.get('return', [])
    if not ret:
        return []
    row       = ret[0]
    ids       = row.get('children.id',   []) or []
    names     = row.get('children.name', []) or []
    types     = row.get('children.type', []) or []
    # 补齐长度（防止某项缺失）
    length = max(len(ids), len(names), len(types))
    ids    = ids   + [''] * (length - len(ids))
    names  = names + [''] * (length - len(names))
    types  = types + [''] * (length - len(types))
    return [{"id": i, "name": n, "type": t} for i, n, t in zip(ids, names, types)]


def get_event_parent_folder(c_obj, src_obj_id):
    """
    获取某个对象所创建的 Play Event 所在父文件夹信息。
    链路：音频对象 → referencesTo(Action) → parent(Event) → parent(Folder/WorkUnit)
    返回 {"path":..., "id":..., "type":...}，未找到则返回 None。
    """
    try:
        refer_info = c_obj.object_get(src_obj_id, ["referencesTo"])['return'][0]
    except Exception:
        return None

    refs = refer_info.get('referencesTo', [])
    if not refs:
        return None

    for ref in refs:
        ref_id = ref.get('id')
        if not ref_id:
            continue
        try:
            action_info = c_obj.object_get(ref_id, ["type", "parent.id", "parent.type", "parent.path"])['return'][0]
        except Exception:
            continue

        if action_info.get('type') == 'Action':
            event_id = action_info.get('parent.id')
            if not event_id:
                continue
            try:
                event_info = c_obj.object_get(event_id, ["parent.path", "parent.id", "parent.type"])['return'][0]
                folder_path = event_info.get('parent.path', '')
                folder_id   = event_info.get('parent.id', '')
                folder_type = event_info.get('parent.type', '')
                if folder_path:
                    return {"path": folder_path, "id": folder_id, "type": folder_type}
            except Exception:
                continue
    return None


def T_Vo_Creat1P_FromActorMixer():
    c_obj = Core_object(client)
    ui    = Ui(client)

    # ── 获取选中对象 ────────────────────────────────────────────────────────
    opt = ["id", "name", "type", "path", "parent.id", "parent.path"]
    objects  = ui.getSelectedObjects(opt)
    obj_list = objects.get("objects", [])

    if not obj_list:
        print("❌ 未选中任何对象，请选择 ActorMixer 后重新运行脚本")
        return None

    created_events = []
    skipped        = []
    errors         = []

    for obj in obj_list:
        if obj['type'] != 'ActorMixer':
            print(f"❌ {obj['name']} 不是 ActorMixer，跳过")
            skipped.append(obj['name'])
            continue

        src_id        = obj['id']
        src_name      = obj['name']
        src_parent_id = obj['parent.id']
        new_name      = f"{src_name}_1P"

        print(f"\n📋 处理源对象：{src_name}")

        # ── Step 1：复制源 ActorMixer 到同父级，重命名为 _1P ────────────────
        copy_result = c_obj.object_copy(src_id, src_parent_id, "rename", ["id", "name", "path"])
        # object.copy 直接返回对象字段（无 'return' 包装层）
        if isinstance(copy_result, dict) and 'return' in copy_result:
            copied_obj = copy_result['return'][0]
        else:
            copied_obj = copy_result

        new_obj_id = copied_obj['id']
        print(f"  ✅ 已复制临时副本：{copied_obj.get('name', new_obj_id)}")

        c_obj.setName(new_obj_id, new_name)
        print(f"  ✅ 已重命名为：{new_name}")

        # ── Step 2 & 3：重命名新对象层级子集 ──────────────────────────────
        # 第一层子集：ActorMixer 加 _1P
        new_l1_children = get_children(c_obj, new_obj_id)
        for l1 in new_l1_children:
            if l1['type'] == 'ActorMixer':
                old_l1_name = l1['name']
                new_l1_name = f"{old_l1_name}_1P"
                c_obj.setName(l1['id'], new_l1_name)
                print(f"    ✅ 第一层 ActorMixer 重命名：{old_l1_name} → {new_l1_name}")

                # 第二层子集：所有对象加 _1P
                new_l2_children = get_children(c_obj, l1['id'])
                for l2 in new_l2_children:
                    old_l2_name = l2['name']
                    new_l2_name = f"{old_l2_name}_1P"
                    c_obj.setName(l2['id'], new_l2_name)
                    print(f"      ✅ 第二层对象重命名：{old_l2_name} → {new_l2_name}")

        # ── Step 4：构建源对象第二层子集 → Event 父路径 的映射 ─────────────
        src_l2_event_map = {}  # key: 源 l2 名称, value: folder info dict or None
        src_l1_children  = get_children(c_obj, src_id)
        for l1 in src_l1_children:
            src_l2_children = get_children(c_obj, l1['id'])
            for l2 in src_l2_children:
                l2_name = l2['name']
                folder_info = get_event_parent_folder(c_obj, l2['id'])
                src_l2_event_map[l2_name] = folder_info
                if folder_info:
                    print(f"  📁 源 {l2_name} → Event 路径：{folder_info['path']}")
                else:
                    print(f"  ⚠️ 源 {l2_name} 未找到已有 Event 路径")

        # ── Step 5：为新对象第二层子集创建 Play Event ──────────────────────
        # 重新获取（已重命名后）新对象第一层子集
        new_l1_children2 = get_children(c_obj, new_obj_id)
        for l1 in new_l1_children2:
            l1_name = l1['name']
            if not l1_name.endswith('_1P'):
                continue

            new_l2_children2 = get_children(c_obj, l1['id'])
            for l2 in new_l2_children2:
                l2_name = l2['name']
                if not l2_name.endswith('_1P'):
                    continue

                src_l2_name = l2_name[:-3]          # 去掉末尾 "_1P" 对应源名称
                folder_info = src_l2_event_map.get(src_l2_name)

                # 用 src_l2_name 最后一个 _ 后的字段替换为 1P
                # 例：src_l2_name = A_A_b -> rsplit('_',1) -> ['A_A', 'b'] -> A_A_1P
                event_name = src_l2_name.rsplit('_', 1)[0] + '_1P'

                if folder_info:
                    folder_path = folder_info['path']
                    folder_type = folder_info['type']
                    # play_event_create(name, id, parent_path, parent_type, parent_name)
                    # parent_path 是父级的父路径，parent_name 是父级名称
                    parts = [p for p in folder_path.split('\\') if p]
                    parent_name    = parts[-1]
                    parent_cr_path = '\\' + '\\'.join(parts[:-1]) if len(parts) > 1 else '\\Events'
                    try:
                        c_obj.play_event_create(
                            event_name, l2['id'],
                            parent_cr_path, folder_type, parent_name,
                            "merge"
                        )
                        created_events.append(f"Play_{event_name} → {folder_path}")
                    except Exception as e:
                        msg = f"创建 Play_{event_name} 失败：{e}"
                        errors.append(msg)
                        print(f"  ❌ {msg}")
                else:
                    # 未找到源 Event 路径，使用默认路径
                    try:
                        c_obj.play_event_create(event_name, l2['id'])
                        created_events.append(f"Play_{event_name} → \\Events（默认）")
                    except Exception as e:
                        msg = f"创建 Play_{event_name} 失败（默认路径）：{e}"
                        errors.append(msg)
                        print(f"  ❌ {msg}")

    # ── 执行结果摘要 ────────────────────────────────────────────────────────
    print("\n" + "═" * 52)
    print("📊 执行结果摘要")
    print("═" * 52)
    if created_events:
        print(f"✅ 成功创建 {len(created_events)} 个 Play Event：")
        for e in created_events:
            print(f"   • {e}")
    if skipped:
        print(f"⚠️  跳过 {len(skipped)} 个非 ActorMixer 对象：{', '.join(skipped)}")
    if errors:
        print(f"❌ 发生 {len(errors)} 个错误：")
        for e in errors:
            print(f"   • {e}")
    if not created_events and not errors and not skipped:
        print("⚠️  未创建任何 Event，请检查源对象是否已有 Event")
    print("═" * 52)


if __name__ == "__main__":
    try:
        client = WaapiClient()
        print("✅ 已连接 Wwise WAAPI")
    except CannotConnectToWaapiException as e:
        print(f"❌ 无法连接 WAAPI：{e}，请打开 Wwise 并确保 WAAPI 已启用")
    else:
        c_undo = Core_undo(client)
        c_undo.undo_beginGroup()

        T_Vo_Creat1P_FromActorMixer()

        c_undo.undo_endGroup("T_Vo_Creat1P_FromActorMixer")

        client.disconnect()
        print("✅ 已断开 WAAPI 连接")

    finally:
        print("\n按任意键退出...")
        msvcrt.getch()
