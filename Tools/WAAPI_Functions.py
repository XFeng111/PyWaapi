class WwiseBase:
    def __init__(self, client:object):
        # 传入外部的client,client = WaapiClient()
        self.client = client

class Core_object(WwiseBase):
    def getChild_SoundId(self, object_id, depth:int=0):
        child_list = []
        max_depth = 100
        if depth > max_depth:
            print(f"递归深度超过限制，终止：object_id={object_id}\n")
            exit() # 终止脚本

        res_children = self.object_get(object_id, opt=["children.id", "children.type"])['return']
        for child in res_children:
            child_id_list = child['children.id']
            child_type_list = child['children.type']
            for child_id, child_type in zip(child_id_list, child_type_list):
                if child_type == "Sound":
                    child_list.append(child_id)
                else:
                    child_list += self.getChild_SoundId(child_id, depth+1)
            
            if child_id_list == [] and child_type_list == []:
                print(f"未找到子对象：object_id={object_id}")
                exit() # 终止脚本

        return child_list

    # res_child = getChild_SoundId("{874CC972-8752-4D28-9563-0ABFCEFA1DCB}")
    # pprint(res_child)

    def audio_import(self, originalsSubFolder, audioFile, objectPath, objectType, opt:list, importOperation:str="useExisting"):
        args = {
            # useExisting ：使用现有对象（如有），更新给定属性；否则，创建新的对象。该项为默认值。
            # replaceExisting ：创建新的对象；若存在同名的现有对象，则将现有对象销毁。
            # createNew ：创建新的对象；在可能的情况下赋予对象以所需名称，否则使用新的唯一名称。

            "importOperation": importOperation, 
            "default": {
                "importLanguage": "SFX"
            },
            "imports": [
                {
                    "originalsSubFolder":originalsSubFolder,
                    "audioFile": audioFile,
                    "objectPath": objectPath,
                    "objectType":objectType
                }
            ]
        }
        options = {
            "return": opt
        }
        return self.client.call("ak.wwise.core.audio.import", args, options=options)

    def setProperty(self, object_id, property, value):
        args ={
                "object": object_id,
                "property": property,
                "value": value
                }
        return self.client.call("ak.wwise.core.object.setProperty",args)

    def object_setName(self, object_id, new_name):
        args = {
            "object": object_id,
            "value": new_name
        }
        return self.client.call("ak.wwise.core.object.setName", args)

    def setName(self, object_id, value):
        args ={
                "object": object_id,
                "value": value
                }
        return self.client.call("ak.wwise.core.object.setName",args)

    def pasteProperties(self, source_id, targets_id, pasteMode:str="replaceEntire"):
        args = {
            "source": source_id,
            "targets": [targets_id],
            "pasteMode": pasteMode
            # inclusion:list = [], 所要包含的属性、引用和列表
            # exclusion :list = [], 所要排除的属性、引用和列表
        }
        
        return self.client.call("ak.wwise.core.object.pasteProperties", args)

    def object_delete(self, object):
        args = {
            "object": object
        }
        return self.client.call("ak.wwise.core.object.delete", args)

    def object_get(self, object_id, opt:list):
        args = {
            "waql": f"$\"{object_id}\""
        }
        options = {
            "return": opt
        }
        return self.client.call("ak.wwise.core.object.get", args, options=options)
        # ['return'][0]['...']['...'] 取值
    
    def play_event_create(self, 
                          event_name, 
                          target_id, 
                          parent_path:str="\\Events", 
                          parent_type:str="WorkUnit", 
                          parent_name:str="Default Work Unit", 
                          onNameConflict:str="merge"):
        args = {
            "parent": parent_path,
            "type": parent_type,
            "name": parent_name,
            "onNameConflict": onNameConflict,
            "children": [
                {
                    "type": "Event",
                    "name": f"Play_{event_name}",
                    "children":[
                        {
                            "name": "",
                            "type": "Action",
                            "@ActionType": 1,
                            "@Target": target_id
                        }
                    ]
                }
            ]
        }
        print(f"✅ 创建事件 Play_{event_name}, 路径：{parent_path}\\{parent_name}\\Play_{event_name}")
        return self.client.call("ak.wwise.core.object.create", args)
    
    def stop_event_create(self, 
                          event_name, 
                          target_id, 
                          parent_path:str="\\Events", 
                          parent_type:str="WorkUnit", 
                          parent_name:str="Default Work Unit", 
                          onNameConflict:str="merge"):
        args = {
            "parent": parent_path,
            "type": parent_type,
            "name": parent_name,
            "onNameConflict": onNameConflict,
            "children": [
                {
                    "type": "Event",
                    "name": f"Stop_{event_name}",
                    "children":[
                        {
                            "name": "",
                            "type": "Action",
                            "@ActionType": 2,
                            "@Target": target_id,
                            "@Scope": 1,
                            "@FadeTime": 0.8
                        }
                    ]
                }
            ]
        }
        print(f"✅ 创建事件 Stop_{event_name}, 路径：{parent_path}\\{parent_name}\\Stop_{event_name}")
        return self.client.call("ak.wwise.core.object.create", args)

    def sourceControl_add(self, file):
        args = {
            "files": [file]
        }
        return self.client.call("ak.wwise.core.sourceControl.add", args)
    
    def sourceControl_delete(self, file):
        args = {
            "files": [file]
        }
        return self.client.call("ak.wwise.core.sourceControl.delete", args)

class Core_undo(WwiseBase):
    def undo_beginGroup(self):
        return self.client.call("ak.wwise.core.undo.beginGroup")
    
    def undo_endGroup(self, displayName:str):
        return self.client.call("ak.wwise.core.undo.endGroup", {"displayName": displayName})
        # displayName 在历史记录中针对此 Undo Group 显示的名称
        # client.call("ak.wwise.core.undo.endGroup", {"displayName": "T_Event_Creat_FromActorMixer"})

class Ui(WwiseBase):
    def getSelectedObjects(self, opt:list):
        options= {
            "return":opt
        }
        return self.client.call("ak.wwise.ui.getSelectedObjects",options=options)
        # ["objects"][0]["..."]["..."] 取值
