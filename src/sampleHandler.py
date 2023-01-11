import serial
import time
from scipy.io import savemat
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

class sampleHandler():
    def __init__(self):
        
        self.OASISData = None
        self.t  = None
        
        # Dynamic Acquisition Parameters --------------------------------------------------
        self.Device = None
        self.t_sample = None
        self.f_sample = None
        self.VoltageRange = None
        self.Offset = None
        self.PRECACHE_SIZE = None
        self.sync_mode = None

        return
    
    def getAcquisitionParameters(self, Window, Device):
        
        # Acquisition Parameters --------------------------------------------------
        self.Device = Device
        self.serialSpeed = Device[3]
        self.t_sample = float(Window.lineEdit.text())
        self.f_sample = int(Window.lineEdit_2.text())
        self.VoltageRange = np.array([float(Window.comboBox_2.currentText()), float(Window.comboBox_3.currentText()), float(Window.comboBox_4.currentText()), float(Window.comboBox_5.currentText())])
        self.triggeredSample = Window.checkBox_3.isChecked()
        self.V_TRIGG_set = float(Window.lineEdit_3.text())

        # Sync mode
        if Window.checkBox_6.isChecked():
            if Window.radioButton.isChecked():
                self.sync_mode = 1
            else:
                self.sync_mode = 2
        else:
            self.sync_mode = 0

    def SampleSerial(self, printLogSignal, sampleAborted, sampleProgress):
        
        # Predefined Acquisition Parameters --------------------------------------------------
        CACHE_SIZE = 1500
        V_TRIGG = 0
        Offset = 0
        PRECACHE_SIZE = 0
        
        # Device depended parameters--------------------------------------------------
        BYTES_PER_SAMPLE = int(int(self.Device[1][2])/2)
        BYTES_PER_CACHE = BYTES_PER_SAMPLE * CACHE_SIZE
        
        # Triggered Sampling --------------------------------------------------
        if self.triggeredSample:
            V_TRIGG = self.V_TRIGG_set
            PRECACHE_SIZE = 1000
            OASISDataRawPreTrigg = np.zeros([PRECACHE_SIZE, BYTES_PER_SAMPLE])
            Offset = 1

        # Variables --------------------------------------------------
        VoltageRangeID = np.zeros(4,int)
        OASISDataRawMain = np.zeros([int(self.t_sample*self.f_sample) - Offset, BYTES_PER_SAMPLE])
        OASISChannelData = np.zeros([PRECACHE_SIZE + int(self.t_sample*self.f_sample) - Offset, 4])
        OASISRcvBuffer = np.zeros([int(self.t_sample*self.f_sample) * BYTES_PER_SAMPLE - Offset*BYTES_PER_SAMPLE])
        self.OASISData = np.zeros([4, PRECACHE_SIZE + int(self.t_sample*self.f_sample)-Offset])
            

        # Serial Connection --------------------------------------------------
        try:
            OASISSerial = serial.Serial(port=self.Device[0], baudrate=self.serialSpeed, timeout=2)
        except (OSError, serial.SerialException):
            printLogSignal.emit("[OASIS-GUI]: DEVICE ERROR! Could not open serial communication.\n")
            printLogSignal.emit("[OASIS-GUI]: Data Acquisition aborted.\n")
            sampleAborted.emit()
            return
        
        while OASISSerial.inWaiting():
            SerialAnswer = OASISSerial.readline()
            if SerialAnswer !=bytes("","utf-8"):
                if SerialAnswer.startswith(bytes("[OASIS]","utf-8")):
                    printLogSignal.emit(SerialAnswer.decode("utf-8",errors="ignore"))
                else:
                    printLogSignal.emit("[OASIS-GUI]: DEVICE ERROR! Unexpected serial communication content.\n")
                    printLogSignal.emit("[OASIS-GUI]: Data Acquisition aborted.\n")
                    sampleAborted.emit()
                    return

        # Set Voltage Ranges --------------------------------------------------
        for k in range(0,4):
            if self.VoltageRange[k]==2.5:
                VoltageRangeID[k] = 1
            elif self.VoltageRange[k]==5:
                VoltageRangeID[k] = 2
            elif self.VoltageRange[k]==6.25:
                VoltageRangeID[k] = 3
            elif self.VoltageRange[k]==10:
                VoltageRangeID[k] = 4
            elif self.VoltageRange[k]==12.5:
                VoltageRangeID[k] = 5
            else:
                raise ValueError("Voltage Range " + str(self.VoltageRange[k]) + " for channel " + str(k+1) + " is invalid.")

        OASISSerial.write(bytes("OASIS.SetVoltageRange(" + str(VoltageRangeID[0]) + "," + str(VoltageRangeID[1]) + "," + str(VoltageRangeID[2]) + ","  + 
                str(VoltageRangeID[3]) + ")","utf-8"))

        while True:
            if OASISSerial.inWaiting():
                SerialAnswer = OASISSerial.readline()
                if SerialAnswer!=bytes("[OASIS] Voltage ranges set.\r\n","utf-8"):
                    if SerialAnswer !=bytes("","utf-8"):
                        printLogSignal.emit(SerialAnswer.decode("utf-8",errors="ignore"))
                else:
                    break
 
        # Start Data Acquisition --------------------------------------------------
        OASISSerial.write(bytes("OASIS.Sample(" + str(self.t_sample) + "," + str(self.f_sample) + "," + str(V_TRIGG) + "," + str(self.sync_mode) + ")","utf-8")) # WSS hacked in
        
        # Wait for incoming data --------------------------------------------------
        while True:
            SerialAnswer = OASISSerial.readline()
            if SerialAnswer!=bytes("<>\r\n","utf-8"):
                if SerialAnswer==bytes("[OASIS] WiFi is ON. Disabling WiFi for Data Acquisition over Serial...\r\n","utf-8"):
                    then = time.time()
                    while time.time()-then<4:
                        pass
                    OASISSerial.write(bytes("OASIS.Sample(" + str(self.t_sample) + "," + str(self.f_sample) + "," + str(V_TRIGG) + "," + str(self.sync_mode) + ")","utf-8")) # WSS hacked in
                if SerialAnswer !=bytes("","utf-8"):
                    printLogSignal.emit(SerialAnswer.decode("utf-8",errors="ignore"))
            else:
                break
        
        dataRcv = 0
        
        # Read buffer and sort in array --------------------------------------------------
        while dataRcv != (int(self.t_sample*self.f_sample/CACHE_SIZE)*BYTES_PER_CACHE):
            if(OASISSerial.inWaiting()):
                _OASISRcvBuffer = OASISSerial.read(BYTES_PER_CACHE)
                
                if(len(_OASISRcvBuffer)!=BYTES_PER_CACHE):
                    printLogSignal.emit("[OASIS-GUI]: DEVICE ERROR! Unexpected serial communication timeout.\n")
                    printLogSignal.emit("[OASIS-GUI]: Data Acquisition aborted.\n")
                    sampleAborted.emit()
                    return
                    
                for i, _byte in enumerate(_OASISRcvBuffer):
                    OASISRcvBuffer[i+dataRcv]=_byte
                    tmp = i
            
                dataRcv += tmp + 1
                sampleProgress.emit(int(dataRcv/(int(self.t_sample*self.f_sample/CACHE_SIZE)*BYTES_PER_CACHE)*100))
                
        _OASISRcvBuffer = OASISSerial.read(int(self.t_sample*self.f_sample*BYTES_PER_SAMPLE)-int(self.t_sample*self.f_sample/CACHE_SIZE)*BYTES_PER_CACHE - BYTES_PER_SAMPLE*Offset)
    
        for i, _byte in enumerate(_OASISRcvBuffer):
            OASISRcvBuffer[i+dataRcv]=_byte

        if(len(OASISRcvBuffer)==(int(self.t_sample*self.f_sample) * BYTES_PER_SAMPLE - Offset*BYTES_PER_SAMPLE)):
            sampleProgress.emit(100)
        else:
            printLogSignal.emit("[OASIS-GUI]: DEVICE ERROR! Data has been lost during transmission.\n")
            printLogSignal.emit("[OASIS-GUI]: Data Acquisition aborted.\n")
            sampleAborted.emit()
            return

        
        for i, _byte in enumerate(OASISRcvBuffer):
            OASISDataRawMain[int(i/BYTES_PER_SAMPLE),i%BYTES_PER_SAMPLE]=_byte
        
        # Convert to Integer --------------------------------------------------
        OASISDataRawMain = OASISDataRawMain.astype(int)
        
        # If Triggered sampling acquire Pre-Trigg Data; assemble everything into one array --------------------------------------------------
        if self.triggeredSample:
            
            # Retrieve Pre-Trigger Data
            OASISSerial.write(bytes("Drq()","utf-8"))
            
            # Wait for incoming data
            while True:
                SerialAnswer = OASISSerial.readline()
                if SerialAnswer==bytes("<>\r\n","utf-8"):
                    break
            
            # Let the buffer fill with the data
            then = time.time()
            
            while time.time()-then<1:
                pass
            
            # Read buffer and sort in array
            _OASISDataRawPreTrigg = OASISSerial.read(OASISSerial.inWaiting())
            
            for i, _byte in enumerate(_OASISDataRawPreTrigg):
                OASISDataRawPreTrigg[int(i/BYTES_PER_SAMPLE),i%BYTES_PER_SAMPLE]=_byte
                
            # Convert to Integer
            OASISDataRawPreTrigg = OASISDataRawPreTrigg.astype(int)
            
            OASISDataRaw = np.concatenate((OASISDataRawPreTrigg,OASISDataRawMain))
            
        else:
            OASISDataRaw = OASISDataRawMain
            
        OASISSerial.close()
        
        printLogSignal.emit("[OASIS] Data Acquisition finished.\n")

        # Seperation of channel bits --------------------------------------------------
        if(BYTES_PER_SAMPLE==9):
            for k in range(0,len(OASISDataRaw)):
                OASISChannelData[k,0] = (OASISDataRaw[k,0] << 10) + (OASISDataRaw[k,1] << 2) + (OASISDataRaw[k,2] >> 6)
                OASISChannelData[k,1] = ((OASISDataRaw[k,2]-((OASISDataRaw[k,2] >> 6) << 6)) << 12) + (OASISDataRaw[k,3] << 4) + (OASISDataRaw[k,4] >> 4)
                OASISChannelData[k,2] = ((OASISDataRaw[k,4]-((OASISDataRaw[k,4] >> 4) << 4)) << 14) + (OASISDataRaw[k,5] << 6) + (OASISDataRaw[k,6] >> 2)
                OASISChannelData[k,3] = ((OASISDataRaw[k,6]-((OASISDataRaw[k,6] >> 2) << 2)) << 16) + (OASISDataRaw[k,7] << 8) + (OASISDataRaw[k,8])
                
        if(BYTES_PER_SAMPLE==8):
            for k in range(0,len(OASISDataRaw)):
                OASISChannelData[k,0] = (OASISDataRaw[k,0] << 8) + (OASISDataRaw[k,1])
                OASISChannelData[k,1] = (OASISDataRaw[k,2] << 8) + (OASISDataRaw[k,3])
                OASISChannelData[k,2] = (OASISDataRaw[k,4] << 8) + (OASISDataRaw[k,5])
                OASISChannelData[k,3] = (OASISDataRaw[k,6] << 8) + (OASISDataRaw[k,7])
                
        # Convert to Voltage --------------------------------------------------
        BitDivider = 2**int(self.Device[1][2])/2
        
        for k in range(0,len(OASISDataRaw)):
            for i in range(0,4):
                if OASISChannelData[k,i]/BitDivider <= 1:
                    self.OASISData[i,k] = (OASISChannelData[k,i]*self.VoltageRange[i])/BitDivider;
                else:
                    self.OASISData[i,k] = ((OASISChannelData[k,i]-2*BitDivider)/BitDivider)*self.VoltageRange[i];
        
        # Assemble time vector --------------------------------------------------
        if self.triggeredSample:
            N = np.arange((1-PRECACHE_SIZE), self.t_sample*self.f_sample, 1)
            self.t = N/self.f_sample
        else:
            self.t = np.arange(0, self.t_sample, 1/self.f_sample)

    def plotData(self):
        # Data plot --------------------------------------------------
        fig, axs = plt.subplots(2, 2)
        j = 0
        for k in range(0,4):
            if k==2:
                j = 1
            fig.set_size_inches(18, 10.5, forward=True)
            axs[j, k-j*2].plot(self.t,self.OASISData[k])
            axs[j, k-j*2].set_title("Channel" + str(k+1))
            axs[j, k-j*2].set_xlabel("Time / s")
            axs[j, k-j*2].set_ylabel("Voltage / V")
            
        if self.triggeredSample:
            axs[0,0].axvline(0,color='black',linestyle='--')
        plt.tight_layout()
        plt.show()

    def saveData(self, Window):
        # Save Data --------------------------------------------------
        saveName = "OASISData-" + Window.LastSampleDevice + "-" + datetime.now().strftime("%Y-%m-%d-%H.%M.%S") +".mat"

        Window.textEdit.append(f"[OASIS-GUI]: Saving acquired data as {saveName}\n")

        try:
            savemat(saveName, {'OASISChannel1': self.OASISData[0], 'OASISChannel2': self.OASISData[1], 'OASISChannel3': self.OASISData[2], 'OASISChannel4': self.OASISData[3], 'OASISTime': self.t})
            Window.textEdit.append(f"[OASIS-GUI]: {saveName} successfully saved.\n")
        except PermissionError:
            Window.textEdit.append("[OASIS-GUI]: ERROR! Can not write to filesystem. Are you running as admin?\n")
            Window.progressBar_2.setVisible(True)

        return saveName