from PyQt6.QtCore import QThread, pyqtSignal
from opcua import Client
from opcua.common.subscription import SubHandler
import time

class MySubHandler(SubHandler):
    def __init__(self):
        super().__init__()
        self.node_values = {}

    def datachange_notification(self, node, val, data):
        try:
            attributes = vars(val)
        except TypeError:
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
        
class OpcuaThread(QThread):
    statusSignal = pyqtSignal(int)
    showMessageSignal = pyqtSignal(str)
    exceptionSignal = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)
        self.url = "opc.tcp://localhost:4840"
        self.username = "admin1"
        self.password = "admin1"

        self.client = None
        self.prev_server_connected = False
        self.prev_status = None

        self.failed_attempts = 0
        self.is_sub = False
        self.is_terminating = False

        self.my_sub_handler = MySubHandler()
        self.node_list = ["ns=4;s=MAIN.myVar1", "ns=4;s=MAIN.myVar2"]
        self.active_subscriptions = []
        self.subscription_info = {}
        
    def run(self):
        self.opcua_server_connect()  # Try to connect once at the start of the thread
        while True:  # Keep the thread running
            self.check_server_status()  # Continuously check the server status

            # Rest a bit to avoid busy looping
            time.sleep(2)  # Or adjust the sleep duration as per your needs

    def opcua_server_connect(self, retries = 3):
        wait_time = 2  # Initial wait time between retries
        for i in range(retries):
            try:
                self.client = Client(self.url)
                self.client.set_user(self.username)
                self.client.set_password(self.password)
                self.client.connect()
                self.showMessageSignal.emit("Connected to OPC UA server") # Emitting signal
                self.client.load_type_definitions()
                self.setup()
                return True  # return True when connection is successful
            except Exception as e:
                self.showMessageSignal.emit(f"Error occurred while trying to connect to the OPC UA server on attempt {i+1}: {str(e)}")
                if i < retries - 1:  # Don't wait after the last attempt
                    time.sleep(wait_time)  # Wait for an increasing time before retrying
                    wait_time *= 2  # Double the wait time for the next retry

        # If it gets to this point, it means all retries have been exhausted
        self.showMessageSignal.emit("Failed to connect to the OPC UA server after multiple retries. Terminating connection attempts.")
        self.is_terminating = True  # set the is_terminating flag to True to stop retry attempts
        return False  # return False when connection fails after retries

    def setup(self):
        # Get the node once and store it
        if self.client is not None:
            try:
                self.bBOOL1 = self.client.get_node("ns=4;s=OPCUA.bBOOL1")
            except Exception as e:
                 self.exceptionSignal.emit(f"Error while getting the bBOOL1 node: {e}")

    def opcua_server_disconnect(self):
        if self.client is not None:
            try:
                if self.subscription_info:
                    single_subscription, _ = list(self.subscription_info.values())[0]
                    try:
                        for _, (_, handle) in self.subscription_info.items():
                            # Check if the subscription is still active before unsubscribing
                            if single_subscription in self.active_subscriptions:
                                single_subscription.unsubscribe(handle)
                                time.sleep(0.1)
                        single_subscription.delete()
                        time.sleep(0.1)
                        if single_subscription in self.active_subscriptions:
                            self.active_subscriptions.remove(single_subscription)
                    except Exception as e:
                        print(f"Error while unsubscribing from subscription: {e}")
                        self.exceptionSignal.emit(f"Error while unsubscribing from subscription: {e}")

                    self.subscription_info.clear()

                self.client.disconnect()
                print("Disconnected from OPC UA server")
                self.exceptionSignal.emit("Disconnected from OPC UA server")
            except Exception as e:
                print(f"Error disconnecting from OPC UA server: {e}")
                self.exceptionSignal.emit(f"Error disconnecting from OPC UA server: {e}")
        else:
            print("OPC UA client not initialized or already disconnected")
            self.exceptionSignal.emit("OPC UA client not initialized or already disconnected")

    def delete_subscriptions(self):
        if self.client is not None:
            try:
                if self.subscription_info:
                    single_subscription, _ = list(self.subscription_info.values())[0]
                    try:
                        single_subscription.delete()
                        time.sleep(0.1)
                        self.active_subscriptions.remove(single_subscription)
                    except Exception as e:
                        self.exceptionSignal.emit(f"Error while deleting subscription: {e}")

                    self.subscription_info.clear()

                self.exceptionSignal.emit("Subscriptions deleted")
            except Exception as e:
                self.exceptionSignal.emit(f"Error deleting subscriptions: {e}")
        else:
            self.exceptionSignal.emit("OPC UA client not initialized or already disconnected")

    def subscribe_to_nodes(self):
        if self.client is not None:
            try:
                self.client.load_type_definitions()
                single_subscription = self.client.create_subscription(100, self.my_sub_handler)
                self.active_subscriptions.append(single_subscription)
                for node_id in self.node_list:
                    handle = single_subscription.subscribe_data_change(self.client.get_node(node_id))
                    self.showMessageSignal.emit(f"Subscribed to data changes for {node_id}")
                    self.subscription_info[node_id] = (single_subscription, handle)
                time.sleep(1)
                self.is_sub = True
            except Exception as e:
                self.exceptionSignal.emit(f"Error subscribing to data changes for nodes: {e}")
        else:
            self.exceptionSignal.emit("OPC UA client not initialized or already disconnected")
                
    def is_connected(self):
        if self.client is None:
            return False
        try:
            self.client.get_endpoints()
            return True
        except Exception:
            return False

    def get_status(self):
        # Check the value of the node
        if self.client is not None and hasattr(self, 'bBOOL1'):
            try:
                self.BOOL1 = self.bBOOL1.get_value()
                return True
            except Exception as e:
                return False
            
    def get_all_node_values(self):
            return self.my_sub_handler.node_values

    def check_server_status(self):
        serverStatus = self.is_connected()
        nodeStatus = None
        if serverStatus:
            nodeStatus = self.get_status()  # Only get node status if server is connected

        if serverStatus != self.prev_server_connected:
            if not serverStatus:
                if not self.is_terminating:
                    self.statusSignal.emit(0)
                    self.delete_subscriptions()
                    if not self.opcua_server_connect():  # Try to reconnect and check if it was successful
                        return  # Exit the method if reconnection failed after retries
            else:
                if nodeStatus:  # using the return value of get_status
                    self.statusSignal.emit(1)
                    self.subscribe_to_nodes()  # Assuming this method sets up your subscription
                else:
                    self.statusSignal.emit(2)
                    # Any additional actions for this case go here...

        self.prev_server_connected = serverStatus

