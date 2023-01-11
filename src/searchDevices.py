import serial
import serial.tools.list_ports
import time

from PyQt5 import QtGui

class searchDevices():
    def __init__(self):
        
        self.Devices = []
        
        return
        
    def SerialSearch(self, printLogSignal):
        
        self.Devices = []
        
        printLogSignal.emit("[OASIS-GUI]: Searching devices...\n")
        
        self.serialSpeed = 2000000
    
        # Search all available COM devices
        comlist = serial.tools.list_ports.comports()
        connected = []
        for element in comlist:
            connected.append(element.device)
        
        if connected:
            
            for DeviceNum in range(0, len(connected)):
                printLogSignal.emit("[OASIS-GUI]: Found device on port " + connected[DeviceNum] + "\n")
                printLogSignal.emit("[OASIS-GUI]: Resetting device...\n")
                
                # Connect to Serial Device and Reset
                try:
                    s = serial.Serial(port=connected[DeviceNum], baudrate=self.serialSpeed, timeout=2)
                except (OSError, serial.SerialException):
                    printLogSignal.emit("[OASIS-GUI]: DEVICE ERROR! Could not open serial communication.\n")
                    continue
                
                s.setDTR(False)
                time.sleep(0.022)
                s.setDTR(True)
                s.readline()
                
                while True:
                    SerialAnswer = s.readline()
                    if SerialAnswer.startswith(bytes("[OASIS]","utf-8")):
                        printLogSignal.emit(SerialAnswer.decode("utf-8",errors="ignore"))
                        if SerialAnswer == bytes("[OASIS] Finished booting.\r\n","utf-8"):
                            
                            # Get Device Information
                            s.write(bytes("OASIS.RawInfo()","utf-8"))
                            printLogSignal.emit("[OASIS-GUI]: Getting device info...\n")
                            DeviceInfo = s.readline().decode("utf-8",errors="ignore").split(";")
                            break
                    else:
                      DeviceInfo = [""]
                      break
                  
                s.close
                if(len(DeviceInfo)==7):
                    isOASIS = True
                    printLogSignal.emit("[OASIS-GUI]: Device on port " + connected[DeviceNum] + " is an OASIS board\n")
                else:
                    isOASIS = False
                    printLogSignal.emit("[OASIS-GUI]: Device on port " + connected[DeviceNum] + " is unknown or does not respond\n")
                
                self.Devices.append([connected[DeviceNum],DeviceInfo,isOASIS,self.serialSpeed])
            
        else:
            printLogSignal.emit("[OASIS-GUI]: Did not find any devices\n")
            
        return
    
    def UpdateDeviceList(self, Window):
        
        # Clear Device List Combobox
        Window.comboBox.clear()
        
        # No Devices found
        if(len(self.Devices)==0):
            
            Window.comboBox.setEnabled(False)
            Window.comboBox.addItem("No Devices")
            
        else:
            
            Window.comboBox.setEnabled(True)
            
            # Sort Devices (OASIS first)
            DevicesOASIS = []
            DevicesOther = []
            
            for Device in range(0,len(self.Devices)):
                if(self.Devices[Device][2]):
                    DevicesOASIS.append(self.Devices[Device])
                else:
                    DevicesOther.append(self.Devices[Device])
            
            Window.textEdit.append("[OASIS-GUI]: Found " + str(len(DevicesOASIS)) + " OASIS Board(s) and " + str(len(DevicesOther)) + " unknown device(s).\n")
            Window.textEdit.repaint()
            
            self.Devices = DevicesOASIS
            for i in range(0,len(DevicesOther)):
                self.Devices.append(DevicesOther[i])
            
            for Device in range(0,len(self.Devices)):
                
                # Device found is an OASIS
                if(self.Devices[Device][2]):
                    Window.comboBox.addItem("OASIS V." + self.Devices[Device][1][0] + " - " + self.Devices[Device][1][5] + " (" + self.Devices[Device][0] + ")")
                else:
                    Window.comboBox.addItem("Unknown Device (" + self.Devices[Device][0] + ")")
            
            Window.comboBox.repaint()
            
        return
    
    def UpdateSelectedDevice(self, Window):
        
        DeviceSelected = Window.comboBox.currentIndex()
        
        Window.comboBox_2.clear()
        Window.comboBox_3.clear()
        Window.comboBox_4.clear()
        Window.comboBox_5.clear()
        
        # No Device found
        if(len(self.Devices)==0):
            Window.label_2.setPixmap(QtGui.QPixmap(":/Boards/resources/boards/Unknown.png"))
            Window.label_8.setText("")
            Window.label_9.setText("")
            Window.label_10.setText("")
            Window.label_11.setText("")
            Window.checkBox.setChecked(False)
            Window.checkBox_2.setChecked(False)
            
            # Disable sampling
            Window.tabWidget.setEnabled(False)
            Window.pushButton_2.setEnabled(False)
            
        else:
            if(self.Devices[DeviceSelected][2]):
                
                # Update GUI Text
                Window.label_8.setText(self.Devices[DeviceSelected][1][5])
                Window.label_9.setText(self.Devices[DeviceSelected][1][0])
                Window.label_10.setText(self.Devices[DeviceSelected][1][1])
                
                # Set available Voltage ranges
                if(self.Devices[DeviceSelected][1][2]=="18"):
                    Window.label_11.setText("AD7606C-18 (18 Bit resolution)")
                    Window.comboBox_2.setEnabled(True)
                    Window.comboBox_2.addItem("2.5")
                    Window.comboBox_2.addItem("5.0")
                    Window.comboBox_2.addItem("6.25")
                    Window.comboBox_2.addItem("10")
                    Window.comboBox_2.addItem("12.5")
                    Window.comboBox_3.setEnabled(True)
                    Window.comboBox_3.addItem("2.5")
                    Window.comboBox_3.addItem("5.0")
                    Window.comboBox_3.addItem("6.25")
                    Window.comboBox_3.addItem("10")
                    Window.comboBox_3.addItem("12.5")
                    Window.comboBox_4.setEnabled(True)
                    Window.comboBox_4.addItem("2.5")
                    Window.comboBox_4.addItem("5.0")
                    Window.comboBox_4.addItem("6.25")
                    Window.comboBox_4.addItem("10")
                    Window.comboBox_4.addItem("12.5")
                    Window.comboBox_5.setEnabled(True)
                    Window.comboBox_5.addItem("2.5")
                    Window.comboBox_5.addItem("5.0")
                    Window.comboBox_5.addItem("6.25")
                    Window.comboBox_5.addItem("10")
                    Window.comboBox_5.addItem("12.5")
                elif(self.Devices[DeviceSelected][1][2]=="16"):
                    Window.label_11.setText("AD7606-4 (16 Bit resolution)")
                    Window.comboBox_2.setEnabled(True)
                    Window.comboBox_3.setEnabled(False)
                    Window.comboBox_4.setEnabled(False)
                    Window.comboBox_5.setEnabled(False)
                    Window.comboBox_2.addItem("5.0")
                    Window.comboBox_2.addItem("10.0")
                    Window.comboBox_3.addItem("5.0")
                    Window.comboBox_3.addItem("10.0")
                    Window.comboBox_4.addItem("5.0")
                    Window.comboBox_4.addItem("10.0")
                    Window.comboBox_5.addItem("5.0")
                    Window.comboBox_5.addItem("10.0")
                else:
                    Window.label_11.setText("Unknown ADC")
                
                # Detect Hardware Features
                if(self.Devices[DeviceSelected][1][3]=="1"):
                    Window.checkBox.setChecked(True)
                else:
                    Window.checkBox.setChecked(False)
                    
                if(self.Devices[DeviceSelected][1][4]=="1"):
                    Window.checkBox_2.setChecked(True)
                    Window.groupBox_5.setEnabled(True)
                    Window.label_21.setEnabled(True)
                else:
                    Window.checkBox_2.setChecked(False)
                    Window.groupBox_5.setEnabled(False)
                    Window.label_21.setEnabled(False)
                
                # Set Board Image
                if(self.Devices[DeviceSelected][1][0]=="1.0"):
                    Window.label_2.setPixmap(QtGui.QPixmap(":/Boards/resources/boards/OASISV1.png"))
        
                # Enable sampling
                Window.tabWidget.setEnabled(True)
                Window.pushButton_2.setEnabled(True)
                
            else:
                Window.label_2.setPixmap(QtGui.QPixmap(":/Boards/resources/boards/Unknown.png"))
                Window.label_8.setText("Unknown")
                Window.label_9.setText("Unknown")
                Window.label_10.setText("Unknown")
                Window.label_11.setText("Unknown")
                Window.checkBox.setChecked(False)
                Window.checkBox_2.setChecked(False)
                
                # Disable sampling
                Window.tabWidget.setEnabled(False)
                Window.pushButton_2.setEnabled(False)
                
        return