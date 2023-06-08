from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtGui import QPixmap, QImage, QDoubleValidator
from PyQt6.QtWidgets import QTableWidgetItem, QMenu, QFileDialog, QGraphicsView, QGraphicsScene, QMessageBox
from PyQt6.QtCore import Qt, QLocale
from datetime import datetime

import opcua as ua
import time
import sys

from client_sub import MySubHandler

########################################################################################
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
#######################################################################################

class Ui_MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('gui_v2.0.ui', self)

        self.client = None
        self.server_connected = False  # State of the server connection
        self.prev_server_connected = None 
        self.status = None
        self.initial_attempt = False
        self.error_displayed = False
        self.retry_count = 0  # Counter for connection retries
        self.stackedWidget.setCurrentIndex(0)
        self.stackedWidget_2.setCurrentIndex(0)

        self.url = "opc.tcp://localhost:4840"
        self.username = "admin1"
        self.password = "admin1"
        self.node_list = ["ns=4;s=MAIN.myVar1", "ns=4;s=MAIN.myVar1"]
        self.active_subscriptions = []
        self.subscription_info = {}

        self.connection_check_timer = QtCore.QTimer(self)
        self.connection_check_timer.timeout.connect(self.check_server_status)
        self.connection_check_timer.start(500) 

        self.update_gui_timer = QtCore.QTimer()
        self.update_gui_timer.setInterval(50)
        self.update_gui_timer.timeout.connect(self.update_GUI)

        QtCore.QTimer.singleShot(500, self.opcua_server_connect)

    # update status of the system to the user
    def show_message(self, title, message):
        message = f"{title}: {message}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_position = self.error_handling.rowCount()
        self.error_handling.insertRow(row_position)
        
        self.error_handling.setItem(row_position, 0, QTableWidgetItem(message))
        self.error_handling.setItem(row_position, 1, QTableWidgetItem(timestamp))
        self.error_handling.resizeColumnsToContents()
        self.error_handling.resizeRowsToContents()
        self.error_handling.scrollToBottom()

    def closeEvent(self, event):
        self.update_gui_timer.stop()
        self.connection_check_timer.stop()
        self.opcua_server_disconnect()
        event.accept()  # Accept the close event

    # set the pages between normal, advance and expert user
    def changePage(self, index):
        # Update the stacked widget to show the page corresponding to the selected index
        self.stackedWidget.setCurrentIndex(index)

    # set the mode to continuous or stop and go
    def changeMode(self, index):
        self.stackedWidget_2.setCurrentIndex(index)

    # initiate the widgets and to assign functions to widgets 
    def assign_functions(self):
        self.comboBox.activated.connect(self.changePage)
        self.groupBox_8.updated.connect(self.retrieve_variables_json_measurement)
        self.json_scan_mode.activated.connect(self.changeMode)

    def setup(self):
        # Get the node once and store it
        if self.client is not None:
            try:
                self.bBOOL1 = self.client.get_node("ns=4;s=OPCUA.bBOOL1")
            except Exception as e:
                print("Error while getting the node:", e)

    def opcua_server_connect(self, retries=3):
        for i in range(retries):
            try:
                self.client = ua.Client(self.url)
                self.client.set_user(self.username)
                self.client.set_password(self.password)
                self.client.connect()
                print("Connected to OPC UA server")
                self.client.load_type_definitions()
                self.setup()
                self.server_connected = True
                self.initial_attempt = True
                return  # Exit the function since connection is successful
            except Exception as e:
                self.server_connected = False
                print(f"Error connecting to OPC UA server on attempt {i+1}: {e}")
                self.show_message("Systemstatus", f"Error connecting to OPC UA server on attempt {i+1}")
                if i < retries - 1:  # Don't wait after the last attempt
                    time.sleep(1)  # Wait for 1 second before retrying
        print("All connection attempts failed. Please check your server settings and restart the GUI again.")
        self.show_message("Systemstatus", "All connection attempts failed. Please check your server settings and restart the GUI again.")

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
                        self.active_subscriptions.remove(single_subscription)
                    except Exception as e:
                        print("Error while unsubscribing from subscription:", e)

                    self.subscription_info.clear()

                self.client.disconnect()
                print("Disconnected from OPC UA server")
            except Exception as e:
                print("Error disconnecting from OPC UA server:", e)
        else:
            print("OPC UA client not initialized or already disconnected")

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
                        print("Error while deleting subscription:", e)

                    self.subscription_info.clear()

                print("Subscriptions deleted")
            except Exception as e:
                print("Error deleting subscriptions:", e)
        else:
            print("OPC UA client not initialized or already disconnected")

    def subscribe_to_nodes(self):
        if self.client is not None:
            try:
                self.my_sub_handler = MySubHandler()
                self.client.load_type_definitions()
                single_subscription = self.client.create_subscription(100, self.my_sub_handler)
                self.active_subscriptions.append(single_subscription)
                for node_id in self.node_list:
                    handle = single_subscription.subscribe_data_change(self.client.get_node(node_id))
                    print(f"Subscribed to data changes for {node_id}")
                    self.subscription_info[node_id] = (single_subscription, handle)
            except Exception as e:
                print(f"Error subscribing to data changes for nodes: {e}")
        else:
            print("OPC UA client not initialized or already disconnected")
                
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

    def check_server_status(self):
        self.get_status()
        current_status = self.is_connected()
        if current_status != self.prev_server_connected:
            if not current_status and self.initial_attempt:
                self.status = 0
            elif current_status:
                if self.get_status():
                    self.status = 1
                elif not self.get_status():
                    self.status = 2
            self.gui_main(self.status)
        self.prev_server_connected = current_status

    def update_GUI(self):
        if self.client is not None:
            try:       
                self.BOOL1 = self.bBOOL1.get_value()

                # Reset error flag because update was successful
                self.error_displayed = False
            except Exception as e:
                if not self.error_displayed:
                    print("Error while updating the GUI:", e)
                    self.error_displayed = True

    def gui_main(self, status):
        if status == 0: # Disconnected from OPCUA Server
            print("Disconnected from the server. Attempting to reconnect.")
            self.show_message("Systemstatus", "Disconnected from the server. Attempting to reconnect.")
            self.delete_subscriptions()
            self.update_gui_timer.stop()
            self.opcua_server_connect()
        elif status == 1: # Connected to OPCUA Server and Twincat is in Running mode
            print("System Ready!")
            self.show_message("Systemstatus", "System Ready!")
            self.assign_functions()
            self.subscribe_to_nodes()
            self.update_gui_timer.start()
        elif status == 2: # Connected to OPCUA Server and Twincat is in Config mode
            print("Warning: Twincat is in Config mode. No data received from server.")
            self.show_message("Systemstatus", "Twincat is in Config mode. No data received from server.")
            self.update_gui_timer.stop()

    def retrieve_variables_json_measurement(self):

        print('json parameter file dropped')

        file_name = self.groupBox_8.file_name
        # Retrieve all parameters from Json
        parameters = self.groupBox_8.parameters

        # Retrieve ScanParameter from Json
        scan_parameters = parameters.get('ScanParameter', {})
        self.json_scan_mode_measurement = scan_parameters.get('Mode(StopAndGo/Continuous)', None)
        self.json_zShiftRange_measurement = scan_parameters.get('Z-Shift Range', None)
        self.json_numberOfPositions_measurement = scan_parameters.get('numberOfPositions', None)
        self.json_numberOfImagesPerPosition_measurement = scan_parameters.get('numberOfImagesPerPosition', None)
        self.json_numberOfSkippedImages_measurement = scan_parameters.get('numberOfSkippedImages', None)
        self.json_dso_measurement = scan_parameters.get('distanceSourceObject(mm)', None)
        self.json_dsd_measurement = scan_parameters.get('distanceSourceDetector(mm)', None)

        # Retrieve PreScanParameter from Json
        pre_scan_parameters = parameters.get('PreScanParameter', {})
        self.json_numberOfPositions_prescan_measurement = pre_scan_parameters.get('numberOfPositions', None)
        self.json_numberOfImagesPerPosition_prescan_measurement = pre_scan_parameters.get('numberOfImagesPerPosition', None)

        # Retrieve Normalization from Json
        normalization_parameters = parameters.get('Normalization', {})
        self.json_flatField_Lut_measurement = normalization_parameters.get('normalizationMethod(flat field/lut)', None)
        self.json_Lut_numberOfFrames_measurement = normalization_parameters.get('numberOfDarkFrames', None)
        self.json_Lut_numberOfLutSteps_measurement = normalization_parameters.get('numberOfLutSteps', None)

        # Retrieve ImageSensor0 from Json
        image_sensor0_parameters = parameters.get('ImageSensor0', {})
        self.json_flipValue_measurement = image_sensor0_parameters.get('flipValue', None)
        self.json_exposure_measurement = image_sensor0_parameters.get('exposureTime(ms)', None)
        self.json_gain_master_measurement = image_sensor0_parameters.get('gain(mdB)', None)
        self.json_blacklevel_measurement = image_sensor0_parameters.get('blackLevel', None)

        # Retrieve ImageSensor1 from Json
        image_sensor1_parameters = parameters.get('ImageSensor1', {})
        self.json_gain_slave_measurement = image_sensor1_parameters.get('gain(mdB)', None)

        # Retrieve Scintilator from Json
        scintilator_parameters = parameters.get('Scintilator', {})
        self.json_scintilator_measurement = scintilator_parameters.get('scintilatorId', None)
        self.json_cor_measurement = scintilator_parameters.get('centerOfRotation(pixels)', None)
        self.json_middlePlane_measurement = scintilator_parameters.get('middlePlane(pixels)', None)
        self.json_pixelSize_measurement = scintilator_parameters.get('pixelSize(mm)', None)

        # Retrieve Source from Json
        source_parameters = parameters.get('Source', {})
        self.json_voltage_measurement = source_parameters.get('voltage(kV)', None)
        self.json_current_measurement = source_parameters.get('current(mA)', None)
        self.json_focal_measurement = source_parameters.get('focalSpotSize(small/large)', None)

        # Set Scan name
        self.name.setText(file_name)

        # Set ScanParameter from Json
        if self.json_scan_mode_measurement == "Continuous":
            self.json_scan_mode.setCurrentIndex(0)
            self.json_scan_mode.currentIndexChanged.connect(self.changeMode)
            self.json_continous_frames.setText(str(self.json_numberOfPositions_measurement))
            self.json_StopAndGoOrContinuousMode = False
        else:
            self.json_scan_mode.setCurrentIndex(1)
            self.json_stopngo_positions.setText(str(self.json_numberOfPositions_measurement))
            self.json_stopngo_frames.setText(str(self.json_numberOfImagesPerPosition_measurement))
            self.json_StopAndGoOrContinuousMode = True

        self.json_z_shift.setText(str(self.json_zShiftRange_measurement))
        self.json_skipped_frames.setText(str(self.json_numberOfSkippedImages_measurement))
        self.json_dso.setText(str(self.json_dso_measurement))
        self.json_dsd.setText(str(self.json_dsd_measurement))

        # Set PreScanParameter from Json
        self.json_pre_scan_positions.setText(str(self.json_numberOfPositions_prescan_measurement))
        self.json_pre_scan_frames.setText(str(self.json_numberOfImagesPerPosition_prescan_measurement)) 

        # Set Normalization from Json
        if self.json_flatField_Lut_measurement == "LUT":
            self.json_lut_frames.setText(str(self.json_Lut_numberOfFrames_measurement))
            self.json_lut_steps.setText(str(self.json_Lut_numberOfLutSteps_measurement))
        else:
            self.json_lut_frames.setText(str("0"))
            self.json_lut_steps.setText(str("0")) 

        # Set ImageSensor0 from Json
        self.json_gain_master.setText(str(self.json_gain_master_measurement))
        self.json_flip_value.setText(str(self.json_flipValue_measurement))
        self.json_exposure_time.setText(str(self.json_exposure_measurement))
        self.json_black_level.setText(str(self.json_blacklevel_measurement))

        # Set ImageSensor1 from Json
        self.json_gain_slave.setText(str(self.json_gain_slave_measurement))

        # Set Scintilator from Json
        self.json_scintilator.setText(str(self.json_scintilator_measurement))
        self.json_cor.setText(str(self.json_cor_measurement))
        self.json_middle_plane.setText(str(self.json_middlePlane_measurement))
        self.json_pixel_size.setText(str(self.json_pixelSize_measurement))

        # Set Source from Json
        self.json_kV.setText(str(self.json_voltage_measurement))
        self.json_mA.setText(str(self.json_current_measurement))
        if self.json_focal_measurement == "Small":
            self.json_focal.setCurrentIndex(0)
        else:
            self.json_focal.setCurrentIndex(1)

        self.advance_update_parameters()

    def advance_update_parameters(self):

        self.advance_kV = self.json_kV.text()
        self.advance_mA = self.json_mA.text()
        self.advance_blackLevel = self.json_black_level.text()
        self.advance_lutSteps = self.json_lut_steps.text()

        # stOpcua
        self.advance_fileName = self.name.text()
        self.advance_filePath = self.path.text()
        self.advance_exposureTime = self.json_exposure_time.text()
        self.advance_gainMaster = self.json_gain_master.text()
        self.advance_numberOfFrames = self.json_continous_frames.text()
        self.advance_numberOfPositionsPreScan = self.json_pre_scan_positions.text()
        self.advance_numberOfFramesPreScan = self.json_pre_scan_frames.text()
        self.advance_numberOfPositionsScan = self.json_stopngo_positions.text()
        self.advance_numberOfFramesScan = self.json_stopngo_frames.text()
        self.advance_numberOfSkippedFrames = self.json_skipped_frames.text()
        self.advance_stopAndGoOrContinuous = self.json_StopAndGoOrContinuousMode

        self.advance_scanBinning = self.json_binning_scan.text()
        bins = self.advance_scanBinning.replace(' ', '').split(',')

        # Create a set from the list of bins to remove duplicates
        bin_set = set(bins)
        # Check which bins are present and set the corresponding variables
        self.advance_ScanBin1 = '1' in bin_set
        self.advance_ScanBin2 = '2' in bin_set
        self.advance_ScanBin3 = '3' in bin_set
        self.advance_ScanBin4 = '4' in bin_set
        self.advance_ScanBin5 = '5' in bin_set
        self.advance_ScanBin6 = '6' in bin_set
        self.advance_ScanBin7 = '7' in bin_set
        self.advance_ScanBin8 = '8' in bin_set

        self.advance_preScanBinning = self.json_binning_pre_scan.text()
        bins = self.advance_preScanBinning.replace(' ', '').split(',')

        # Create a set from the list of bins to remove duplicates
        bin_set = set(bins)
        # Check which bins are present and set the corresponding variables
        self.advance_preScanBin1 = '1' in bin_set
        self.advance_preScanBin2 = '2' in bin_set
        self.advance_preScanBin3 = '3' in bin_set
        self.advance_preScanBin4 = '4' in bin_set
        self.advance_preScanBin5 = '5' in bin_set
        self.advance_preScanBin6 = '6' in bin_set
        self.advance_preScanBin7 = '7' in bin_set
        self.advance_preScanBin8 = '8' in bin_set

        if int(self.json_lut_steps.text()) > 2:
            self.advance_LutOrFlatFieldCorrection = False
        else:
            self.advance_LutOrFlatFieldCorrection = True

        print(self.advance_ScanBin1)
        print(self.advance_ScanBin2)
        print(self.advance_ScanBin8)
        print(self.advance_LutOrFlatFieldCorrection)
        print(self.advance_filePath)

        # # stScan
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_

        # # stMain
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_
        # self.advance_


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = Ui_MainWindow()
    mainWindow.show()
    sys.exit(app.exec())