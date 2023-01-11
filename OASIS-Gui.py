import sys
import serial
import time

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.uic import loadUi
from ui.OASISUI import Ui_MainWindow

from src.searchDevices import searchDevices
from src.sampleHandler import sampleHandler

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton, True)

if sys.platform.startswith('win'):
    import ctypes
    myappid = 'OASIS-GUI'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

DeviceSearch = searchDevices()
SampleHandler = sampleHandler()

class WorkerDeviceSearch(QObject):
    
    finished = pyqtSignal()
    printLogSignal = pyqtSignal(str)
    
    def __init__(self, DeviceSearch):
        super(WorkerDeviceSearch, self).__init__()
        self.DeviceSearch = DeviceSearch

    def run(self):
        self.DeviceSearch.SerialSearch(self.printLogSignal)
        self.finished.emit()
        
class WorkerSerialSample(QObject):
    
    finished = pyqtSignal()
    printLogSignal = pyqtSignal(str)
    sampleAborted = pyqtSignal()
    sampleProgress = pyqtSignal(int)
    
    def __init__(self, SampleHandler):
        super(WorkerSerialSample, self).__init__()
        self.SampleHandler = SampleHandler

    def run(self):
        self.SampleHandler.SampleSerial(self.printLogSignal, self.sampleAborted, self.sampleProgress)
        self.finished.emit()

class Window(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.connectSignalsSlots()
        self.progressBar_2.setVisible(False)
        self.label_19.setVisible(False)
        self.movie = QMovie(":/Misc/resources/spin.gif")
        self.label_19.setMovie(self.movie)
        self.movie.start()
        self.DeviceLocked = False
        self.RelockDevice = False
        self.Search_Devices()

    def connectSignalsSlots(self):
        self.actionAbout.triggered.connect(self.About)
        self.actionSearch_Devices.triggered.connect(self.Search_Devices)
        self.actionSerial_Sample.triggered.connect(self.Serial_Sample)
        self.actionDevice_Selected_Changed.triggered.connect(self.Update_Device)
        self.actionRange_Channel1_Changed.triggered.connect(self.Update_Range)
        self.actionshow_Previous_Data.triggered.connect(self.Show_Previous_Data)
        self.actionsave_Previous_Data.triggered.connect(self.Save_Previous_Data)
        self.label_21.mousePressEvent = self.LockDevice

    def About(self):
        dialog = AboutDialog(self)
        dialog.exec()
        
    def Update_Device(self):
        DeviceSearch.UpdateSelectedDevice(self)
        
    def Update_Range(self):
        if DeviceSearch.Devices and len(DeviceSearch.Devices[self.comboBox.currentIndex()][1])==7:
            if(DeviceSearch.Devices[self.comboBox.currentIndex()][1][2]=="16"):
                self.comboBox_3.setCurrentIndex(self.comboBox_2.currentIndex())
                self.comboBox_4.setCurrentIndex(self.comboBox_2.currentIndex())
                self.comboBox_5.setCurrentIndex(self.comboBox_2.currentIndex())
        
    def Search_Devices(self):
        # Lock & Update GUI
        self.pushButton.setEnabled(False)
        self.tabWidget.setEnabled(False)
        self.comboBox.setEnabled(False)
        self.pushButton_3.setEnabled(False)
        self.pushButton_4.setEnabled(False)
        self.textEdit.clear()
        self.label_19.setVisible(True)
        DeviceSearch.Devices = []
        DeviceSearch.UpdateDeviceList(self)
        DeviceSearch.UpdateSelectedDevice(self)
        self.comboBox.setItemText(0, "Searching Devices...")
        
        # Setup Worker & Thread
        self.thread = QThread()
        self.workerDeviceSearch = WorkerDeviceSearch(DeviceSearch)
        self.workerDeviceSearch.moveToThread(self.thread)
        
        # Connect Signals
        self.workerDeviceSearch.finished.connect(self.thread.quit)
        self.workerDeviceSearch.printLogSignal.connect(self.printLog)
        self.thread.started.connect(self.workerDeviceSearch.run)
        self.thread.finished.connect(self.Search_Devices_PostProcess)
        
        self.thread.start()
        
    def Search_Devices_PostProcess(self):
        self.pushButton.setEnabled(True)
        DeviceSearch.UpdateDeviceList(self)
        DeviceSearch.UpdateSelectedDevice(self)
        self.label_19.setVisible(False)
        
    def printLog(self, string):
        self.textEdit.append(string)
        
    def Serial_Sample(self):
        # Lock & Update GUI
        self.tabWidget.setEnabled(False)
        self.pushButton.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.comboBox.setEnabled(False)
        self.progressBar.setValue(0)
        self.progressBar_2.setVisible(False)
        self.groupBox_5.setEnabled(False)
        self.sampleError = False
        self.LastSampleDevice = DeviceSearch.Devices[self.comboBox.currentIndex()][1][5]

        # Release Serial lock
        if self.DeviceLocked:
            try:
                self.LockSerial.close()
                time.sleep(0.5)
            except:
                pass
            self.RelockDevice = True
            self.DeviceLocked = False

        # Get Acquisition Paramters from user input
        SampleHandler.getAcquisitionParameters(self, DeviceSearch.Devices[self.comboBox.currentIndex()])
        
        # Setup Worker & Thread
        self.thread = QThread()
        self.workerSerialSample = WorkerSerialSample(SampleHandler)
        self.workerSerialSample.moveToThread(self.thread)
        
        # Connect Signals
        self.workerSerialSample.finished.connect(self.thread.quit)
        self.workerSerialSample.printLogSignal.connect(self.printLog)
        self.workerSerialSample.sampleAborted.connect(self.abortSample)
        self.workerSerialSample.sampleProgress.connect(self.updateProgressBar)
        self.thread.started.connect(self.workerSerialSample.run)
        self.thread.finished.connect(self.Serial_Sample_PostProcess)
        
        self.thread.start()

    def abortSample(self):
        self.sampleError = True
        self.progressBar_2.setVisible(True)
        self.progressBar.setValue(0)
        self.pushButton.setEnabled(True)
        self.pushButton_2.setEnabled(True)
        self.comboBox.setEnabled(True)
        self.tabWidget.setEnabled(True)

    def updateProgressBar(self, value):
        self.progressBar.setValue(value)
        
    def Serial_Sample_PostProcess(self):
        if self.checkBox_4.isChecked() and not self.sampleError:
            self.Show_Previous_Data()
        if self.checkBox_5.isChecked() and not self.sampleError:
            self.Save_Previous_Data()
        self.pushButton.setEnabled(True)
        self.pushButton_2.setEnabled(True)
        self.pushButton_3.setEnabled(True)
        self.pushButton_4.setEnabled(True)
        if DeviceSearch.Devices[self.comboBox.currentIndex()][1][4]:
            self.groupBox_5.setEnabled(True)
        if self.RelockDevice:
            self.LockDevice("JA")
        if not self.DeviceLocked:
            self.comboBox.setEnabled(True)
        self.tabWidget.setEnabled(True)
        
    def Show_Previous_Data(self):
        SampleHandler.plotData()
    
    def Save_Previous_Data(self):
        SampleHandler.saveData(self)

    def LockDevice(self, garbage):
        self.DeviceLocked = not self.DeviceLocked
        if self.DeviceLocked:
            self.textEdit.append(f"[OASIS-GUI]: Locking {self.comboBox.currentText()}\n")
            try:
                self.LockSerial = serial.Serial(port=DeviceSearch.Devices[self.comboBox.currentIndex()][0], baudrate=DeviceSearch.serialSpeed, timeout=2)
            except (OSError, serial.SerialException):
                self.textEdit.append("[OASIS-GUI]: DEVICE ERROR! Could not lock device.\n")
                self.DeviceLocked = False

            self.comboBox.setEnabled(False)
            self.label_21.setPixmap(QtGui.QPixmap(":/Misc/resources/lock.png"))
        else:
            try:
                self.LockSerial.close()
            except:
                pass

        if not self.DeviceLocked:
            self.textEdit.append(f"[OASIS-GUI]: Unlocking {self.comboBox.currentText()}\n")
            self.comboBox.setEnabled(True)
            self.label_21.setPixmap(QtGui.QPixmap(":/Misc/resources/unlock.png"))

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("ui/OASISGui_About.ui", self)

app = QApplication(sys.argv)

# set app icon    
app_icon = QtGui.QIcon()
app_icon.addFile(':/Icons/resources/icons/16x16.png', QtCore.QSize(16,16))
app_icon.addFile(':/Icons/resources/icons/24x24.png', QtCore.QSize(24,24))
app_icon.addFile(':/Icons/resources/icons/32x32.png', QtCore.QSize(32,32))
app_icon.addFile(':/Icons/resources/icons/48x48.png', QtCore.QSize(48,48))
app_icon.addFile(':/Icons/resources/icons/256x256.png', QtCore.QSize(256,256))
app.setWindowIcon(app_icon)
win = Window()
win.show()
sys.exit(app.exec())