class WwiseBase:
    def __init__(self, client:object):
        # 传入外部的client,client = WaapiClient()
        self.client = client

class Core_object(WwiseBase):
    def setProperty(self, object_id, property, value):
        args ={
                "object": object_id,
                "property": property,
                "value": value
                }
        return self.client.call("ak.wwise.core.object.setProperty",args)

    def object_get(self, object_id, opt:list):
        args = {
            "waql": f"$\"{object_id}\""
        }
        options = {
            "return": opt
        }
        return self.client.call("ak.wwise.core.object.get", args, options=options)
        # ['return'][0]['...']['...'] 取值
    
    def play_event_create(self, event_name, target_id):
        args = {
            "parent":"\\Events",
            "type": "WorkUnit",
            "name": "Default Work Unit",
            "onNameConflict": "merge",
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
        print(f"✅ 创建事件 Play_{event_name}, 路径：\\Events\\Default Work Unit\\Play_{event_name}")
        return self.client.call("ak.wwise.core.object.create", args)
    
    def stop_event_create(self, event_name, target_id):
        args = {
            "parent":"\\Events",
            "type": "WorkUnit",
            "name": "Default Work Unit",
            "onNameConflict": "merge",
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
        print(f"✅ 创建事件 Stop_{event_name}, 路径：\\Events\\Default Work Unit\\Stop_{event_name}")
        return self.client.call("ak.wwise.core.object.create", args)

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
