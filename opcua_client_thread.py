from PyQt6.QtCore import QThread, pyqtSignal
from opcua import Client
from opcua import ua
from opcua.common.subscription import SubHandler
import time

class MySubHandler(SubHandler):
    def __init__(self):
        super().__init__()
        self.node_values = {}
        self.get_attribute_value_error_shown = False 

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
        try:
            if node_id in self.node_values and attribute_name in self.node_values[node_id]:
                return self.node_values[node_id][attribute_name]
            else:
                if not self.get_attribute_value_error_shown:
                    print(f"Attribute {attribute_name} not found for node {node_id}")
                    self.get_attribute_value_error_shown = True
                return None
        except Exception as e:
            if not self.get_attribute_value_error_shown:
                print(f"An error occurred while getting attribute value: {str(e)}")
                self.get_attribute_value_error_shown = True
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
        self.initial_attempt = True
        self.prev_server_connected = False
        self.update_node_values_error_shown = False  

        self.is_sub = False
        self.is_terminating = False
  
        self.my_sub_handler = MySubHandler()
        self.node_list = ["ns=4;s=MAIN.myVar1", "ns=4;s=MAIN.myVar2"]
        self.active_subscriptions = []
        self.subscription_info = {}
        
    def run(self):
        self.opcua_server_connect()  # Try to connect once at the start of the thread
        while not self.is_terminating:  # Keep the thread running until termination is requested

            if self.client and self.is_sub:
                self.update_node_values()

            self.check_server_status()  # Continuously check the server status

    def opcua_server_connect(self, retries = 3):
        wait_time = 2  # Initial wait time between retries
        if self.initial_attempt:
            self.showMessageSignal.emit("Verbindung zum OPC UA Server nicht möglich. Erneuter Verbindungsversuch.")
            self.initial_attempt = False

        for i in range(retries):
            try:
                self.client = Client(self.url)
                self.client.set_user(self.username)
                self.client.set_password(self.password)
                self.client.connect()
                self.client.load_type_definitions()
                self.setup()
                self.showMessageSignal.emit("Verbunden mit OPC UA Server") # Emitting signal
                return True  # return True when connection is successful
            except Exception as e:
                self.exceptionSignal.emit(f"Beim Versuch, eine Verbindung zum OPC UA Server herzustellen, ist ein Fehler aufgetreten {i+1}: {str(e)}")
                if i < retries - 1:  # Don't wait after the last attempt
                    time.sleep(wait_time)  # Wait for an increasing time before retrying
                    wait_time *= 2  # Double the wait time for the next retry

        # If it gets to this point, it means all retries have been exhausted
        self.showMessageSignal.emit("Die Verbindung zum OPC UA Server konnte nach mehreren Versuchen nicht hergestellt werden. Abbruch der Verbindungsversuche.")
        self.showMessageSignal.emit("Bitte überprüfen Sie den OPC UA Server der SPS und starten Sie die GUI neu")
        self.is_terminating = True  # set the is_terminating flag to True to stop retry attempts
        return False  # return False when connection fails after retries
    
    def setup(self):
        # Get the node once and store it
        if self.client is not None:
            try:
                self.bServerStatus = self.client.get_node("ns=4;s=OPCUA.bServerStatus")
            except Exception as e:
                 self.exceptionSignal.emit(f"Fehler beim Abrufen des Knotens bServerStatus: {e}")

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
                        self.exceptionSignal.emit(f"Fehler beim Abmelden vom Abonnement: {e}")

                    self.subscription_info.clear()

                self.client.disconnect()
            except Exception as e:
                self.exceptionSignal.emit(f"Fehler beim Trennen der Verbindung zum OPC UA Server: {e}")
        else:
            self.exceptionSignal.emit("OPC UA Client nicht initialisiert oder bereits getrennt")

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
                        self.exceptionSignal.emit(f"Fehler beim Löschen des Abonnements: {e}")

                    self.subscription_info.clear()

                self.exceptionSignal.emit("Abonnements gelöscht")
            except Exception as e:
                self.exceptionSignal.emit(f"Fehler beim Löschen von Abonnements: {e}")
        else:
            self.exceptionSignal.emit("OPC UA Client nicht initialisiert oder bereits getrennt")

    def subscribe_to_nodes(self):
        if self.client is not None:
            try:
                self.client.load_type_definitions()
                single_subscription = self.client.create_subscription(100, self.my_sub_handler)
                self.active_subscriptions.append(single_subscription)
                all_subscribed = True  # Flag to check if all nodes are subscribed
                for node_id in self.node_list:
                    try:
                        handle = single_subscription.subscribe_data_change(self.client.get_node(node_id))
                        # self.showMessageSignal.emit(f"Subscribed to data changes for {node_id}")
                        self.subscription_info[node_id] = (single_subscription, handle)
                    except Exception as e:  # If an error occurs while subscribing to a node, update the flag
                        all_subscribed = False
                        self.exceptionSignal.emit(f"Fehler beim Abonnieren von Datenänderungen für Knoten {node_id}: {e}")
                # If all nodes were subscribed successfully, emit a message
                if all_subscribed:
                    self.showMessageSignal.emit("Empfang von Daten vom Server")
                    time.sleep(1)
                    self.is_sub = True
            except Exception as e:
                self.exceptionSignal.emit(f"Fehler beim Abonnieren von Datenänderungen für Knoten: {e}")
        else:
            self.exceptionSignal.emit("OPC UA Client nicht initialisiert oder bereits getrennt")
                
    def is_connected(self):
        if self.client is None:
            return False
        try:
            self.client.get_endpoints()
            return True
        except Exception:
            return False

    def get_twincat_status(self):
        # Check the value of the node
        if self.client is not None and hasattr(self, 'bServerStatus'):
            try:
                self.BOOL1 = self.bServerStatus.get_value()
                return True
            except Exception as e:
                return False

    def get_nodes(self):
        try:
            self.nodeMyInt1 = self.client.get_node("ns=4;s=OPCUA.iINT1")
            self.nodeMyInt2 = self.client.get_node("ns=4;s=OPCUA.iINT2") 
        except Exception as e:
            print("Error while getting the nodes:", e)
        
    def update_node_values(self):
        try:
            self.MyInt1 = self.nodeMyInt1.get_value()
            self.MyInt2 = self.nodeMyInt2.get_value()

            if self.is_sub:
                self.myIntVar1 = self.my_sub_handler.get_attribute_value("ns=4;s=MAIN.myVar1", "myInt")
                
            self.update_node_values_error_shown = False 

        except Exception as e:
            if not self.update_node_values_error_shown:
                self.update_node_values_error_shown = True 
                print("Error while updating the nodes:", e)

    def check_server_status(self):
        serverStatus = self.is_connected()
        twincatStatus = None
        if serverStatus:
            twincatStatus = self.get_twincat_status()  # Only get node status if server is connected

        if serverStatus != self.prev_server_connected:
            if not serverStatus:
                if not self.is_terminating:
                    self.statusSignal.emit(0)
                    self.exceptionSignal.emit("Die Verbindung zum Server wurde unterbrochen. Versuche, erneut eine Verbindung herzustellen.")
                    if not self.opcua_server_connect():  # Try to reconnect and check if it was successful
                        return  # Exit the method if reconnection failed after retries
            else:
                if twincatStatus:  # using the return value of get_status
                    self.get_nodes()
                    self.subscribe_to_nodes()  # Assuming this method sets up your subscription
                    self.statusSignal.emit(1)

                else:
                    self.statusSignal.emit(2)
                    self.exceptionSignal.emit("Twincat befindet sich im Config-Modus. Keine Daten vom Server empfangen.")
                    # Any additional actions for this case go here...

        self.prev_server_connected = serverStatus

#------------------------------------------------------------------------------------------------------------#   
    def setValue(self, node, value):
        if isinstance(value, bool):
            variant_type = ua.VariantType.Boolean
        elif isinstance(value, int):
            variant_type = ua.VariantType.UInt32
        elif isinstance(value, float):
            variant_type = ua.VariantType.Double
        elif isinstance(value, str):
            variant_type = ua.VariantType.String
        else:
            raise ValueError(f'Unsupported value type: {type(value)}')

        dv = ua.DataValue(ua.Variant(value, variant_type))
        dv.ServerTimestamp = None
        dv.SourceTimestamp = None
        node.set_value(dv)

    def setBoolean(self, node, value):
        self.setValue(node, value)

    def setPushButton(self, node):
        self.setBoolean(node, True)
        time.sleep(0.1)
        self.setBoolean(node, False)

    def setAbsoluteValues(self, axisNode, value, pushButtonNode):
        try:
            payload = float(value.text())
            self.setValue(axisNode, payload)
            self.setPushButton(pushButtonNode)
        except ValueError:
            return f"Error: Cannot convert '{value.text()}' to float"
        
    def copyOpcuaValues(self, src, dst):
        for attr in dir(src):
            if not callable(getattr(src, attr)) and not attr.startswith("__"):
                setattr(dst, attr, getattr(src, attr))

    def updateOpcuaValues(self, opcuaInstance, updatesDict):
        for key, value in updatesDict.items():
            if hasattr(opcuaInstance, key):
                setattr(opcuaInstance, key, value)
            else:
                print(f"Warning: '{key}' not found in the instance")

    def writeCustomType(self, client, nodeId, customDataTypeInstance, updates):
        # Get the node for the custom data type
        node = client.get_node(nodeId)

        # Create a new instance of the custom data type and copy values from the original instance
        dvCustom = customDataTypeInstance.__class__()
        self.copyOpcuaValues(customDataTypeInstance, dvCustom)

        # Update the custom data type properties with the new values
        self.updateOpcuaValues(dvCustom, updates)

        # Convert the custom data type to DataValue with Variant and write it back to the node
        dvCustom = ua.DataValue(ua.Variant(dvCustom, ua.VariantType.ExtensionObject))
        node.set_value(dvCustom)
#------------------------------------------------------------------------------------------------------------#       