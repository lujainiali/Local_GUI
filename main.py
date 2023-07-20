from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtGui import QPixmap, QImage, QDoubleValidator
from PyQt6.QtWidgets import QTableWidgetItem, QMenu, QFileDialog, QGraphicsView, QGraphicsScene, QMessageBox, QApplication
from PyQt6.QtCore import Qt, QLocale, QThread
from datetime import datetime

import opcua as ua
import time
import sys

from opcua_client_thread import OpcuaThread

########################################################################################
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
#######################################################################################

def test():
    print("here is to test the git add -p method")

def test_2():
    print("here is to test the git add -p method")

class Ui_MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('gui_v2.0.ui', self)
        
        self.updateGui_error_shown = False 
        self.stackedWidget.setCurrentIndex(0)
        self.stackedWidget_2.setCurrentIndex(0)
        self.tabWidget_2.setCurrentIndex(0)

        self.OpcuaThread = OpcuaThread()
        self.OpcuaThread.statusSignal.connect(self.guiMain)
        self.OpcuaThread.showMessageSignal.connect(self.update_text)
        self.OpcuaThread.exceptionSignal.connect(self.update_error_text)
        self.OpcuaThread.start()

        self.updateGui_timer = QtCore.QTimer()
        self.updateGui_timer.setInterval(50)
        self.updateGui_timer.timeout.connect(self.updateGui)

    # update status of the system to the user
    def showMessage(self, title, message):
        message = f"{title}: {message}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_position = self.error_handling.rowCount()
        self.error_handling.insertRow(row_position)
        
        self.error_handling.setItem(row_position, 0, QTableWidgetItem(message))
        self.error_handling.setItem(row_position, 1, QTableWidgetItem(timestamp))
        self.error_handling.resizeColumnsToContents()
        self.error_handling.resizeRowsToContents()
        self.error_handling.scrollToBottom()
    
    def showErrorMessage(self, title, message):
        message = f"{title}: {message}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_position = self.error_handling_2.rowCount()
        self.error_handling_2.insertRow(row_position)
        
        self.error_handling_2.setItem(row_position, 0, QTableWidgetItem(message))
        self.error_handling_2.setItem(row_position, 1, QTableWidgetItem(timestamp))
        self.error_handling_2.resizeColumnsToContents()
        self.error_handling_2.resizeRowsToContents()
        self.error_handling_2.scrollToBottom()

    def update_text(self, message):
       self.showMessage("Verbindungsstatus", message)

    def update_error_text(self, message):
       self.showErrorMessage("Fehlerstatus", message)

    def closeEvent(self, event):
        # Stop the timer (if it's running)
        if self.updateGui_timer.isActive():
            self.updateGui_timer.stop()

        self.OpcuaThread.is_terminating = True

        # Disconnect from OPC UA server
        self.OpcuaThread.opcua_server_disconnect()

        # Stop the thread
        self.OpcuaThread.quit()  # request to stop
        # Accept the close event
        event.accept()

    # set the pages between normal, advance and expert user
    def changePage(self, index):
        # Update the stacked widget to show the page corresponding to the selected index
        self.stackedWidget.setCurrentIndex(index)

    # set the mode to continuous or stop and go
    def changeMode(self, index):
        self.stackedWidget_2.setCurrentIndex(index)

    # initiate the widgets and to assign functions to widgets 
    def assignFunctions(self):
        self.comboBox.activated.connect(self.changePage)
        self.groupBox_8.updated.connect(self.advanceRetrieveVariablesJson)
        self.json_scan_mode.activated.connect(self.changeMode)
        self.einaus_Xray.clicked.connect(self.setParameters)

    def setParameters(self):

        try:

            self.OpcuaThread.setValue(self.nodeMyBool1, False)
            self.OpcuaThread.setValue(self.nodeMyInt1, 100)

            node_id = "ns=4;s=MAIN.myVar1"
            node = self.OpcuaThread.client.get_node(node_id)
            custom_data_type_instance = node.get_value()

            updates_stopcua = {
                "myReal": float(self.file_name),
            }

            # self.OpcuaThread.writeCustomType(self.OpcuaThread.client, node_id, custom_data_type_instance, updates_stopcua)

        except Exception as e:
            print(f"An error occurred while setting parameters: {str(e)}")

    def updateGui(self):
        try:
            self.ZB_nActPos.setText(str(self.OpcuaThread.MyInt1))
            self.R_nActPos.setText(str(self.OpcuaThread.myIntVar1))

            self.directory_path = self.path.text()
            self.file_name = self.name.text()

            self.updateGui_error_shown = False  

        except Exception as e:
            if not self.updateGui_error_shown:
                self.updateGui_error_shown = True  
                print("Error while updating the GUI:", e)

    def advanceRetrieveVariablesJson(self):

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

        self.advanceUpdateParameters()

    def advanceUpdateParameters(self):

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

    def guiMain(self, status):
        if status == 0: # Disconnected from OPCUA Server
            self.updateGui_timer.stop()
            self.showMessage("Systemstatus", "System nicht bereit. Verbindung zum OPC UA Server unterbrochen")

        elif status == 1: # Connected to OPCUA Server and Twincat is in Running mode
            self.assignFunctions()
            self.updateGui_timer.start()
            self.showMessage("Systemstatus", "System bereit")

        elif status == 2: # Connected to OPCUA Server and Twincat is in Config mode
            self.updateGui_timer.stop()
            self.showMessage("Systemstatus", "System nicht bereit. Keine Daten vom Server empfangen.")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = Ui_MainWindow()
    mainWindow.show()
    sys.exit(app.exec())