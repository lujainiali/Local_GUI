from opcua.common.subscription import SubHandler

class MySubHandler(SubHandler):
    def __init__(self):
        super().__init__()
        self.node_values = {}

    def datachange_notification(self, node, val, data):
        try:
            attributes = vars(val)
        except TypeError:
            self.error_flag = True
            print(f"TypeError: {val} does not have a __dict__ attribute")
            return
        node_id_str = node.nodeid.to_string()
        if node_id_str not in self.node_values:
            self.node_values[node_id_str] = {}
        attributes = vars(val)
        for attr_name, attr_value in attributes.items():
            self.node_values[node_id_str][attr_name] = attr_value

    def get_attribute_value(self, node_id, attribute_name):
        if node_id in self.node_values and attribute_name in self.node_values[node_id]:
            return self.node_values[node_id][attribute_name]
        else:
            print(f"Attribute {attribute_name} not found for node {node_id}")
            return None
