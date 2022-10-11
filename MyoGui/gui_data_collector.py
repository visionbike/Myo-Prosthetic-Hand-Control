"""
MIT License

Copyright (c) 2022 Phuc Thanh-Thien Nguyen <https://github.com/visionbike/Myo-Prosthetic-Hand-Control>
Copyright (c) 2022 madwilliam <https://github.com/madwilliam/MyoInterface>
Copyright (c) 2021 Crimson-Crow <https://github.com/Crimson-Crow/pymyo>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import gc
import sys
import time
from collections import deque
from pathlib import Path
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtCore import Qt, QRect, QLocale, QTimer, Signal, Slot
from PySide6.QtWidgets import QVBoxLayout, QGridLayout
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox
from PySide6.QtWidgets import QGroupBox, QPushButton, QTextBrowser, QLabel, QLineEdit, QComboBox
import pyqtgraph as pg
from pyqtgraph import PlotWidget
from qasync import QEventLoop, asyncSlot
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from qmyo import QMyo

pg.setConfigOptions(leftButtonPan=False)


class MainWindow(QMainWindow):
    signal_streamed = Signal(bool)

    def __init__(self):
        super(MainWindow, self).__init__()

        self.gesture          = 'default'
        self.repetition       = 5
        self.count_repetition = 1
        self.sample_displayed = 800
        self._dir             = str(Path().absolute())

        self._myo             = None
        self._connected       = False
        self._streamed        = False
        self.first_start      = False

        self.timer = QTimer(self)

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Setup GUI

        :return:
        """

        # setup ui for components
        self._init_ui_emg()
        self._init_ui_status()
        self._init_ui_directory()
        self._init_ui_file()
        self._init_ui_discover()
        self._init_ui_button()
        self._init_ui_console()

        # activate/deactivate some buttons and text boxes
        self.btn_dir.setEnabled(True)
        self.btn_discover.setEnabled(True)
        self.btn_conn.setEnabled(True)
        self.btn_disconn.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_save.setEnabled(False)
        #
        self.cbx_device.setEnabled(True)
        #
        self.lne_gesture.setEnabled(True)
        self.lne_repetition.setEnabled(True)

        # connect signals
        self.btn_dir.clicked.connect(self.handle_directory)
        self.btn_discover.clicked.connect(self.handle_discover)
        self.btn_conn.clicked.connect(self.handle_connect)
        self.btn_disconn.clicked.connect(self.handle_disconnect)
        self.btn_start.clicked.connect(self.handle_start)
        self.btn_save.clicked.connect(self.handle_save)
        #
        self.lne_gesture.editingFinished.connect(self.handle_editingfinished_gesture)
        self.lne_repetition.editingFinished.connect(self.handle_editingfinished_repetition)

        # set ui for the main window
        self.setWindowTitle('Myo Data Collector')
        self.setFixedSize(1330, 860)

    def _init_ui_emg(self) -> None:
        self.gbx_emg = QGroupBox('sEMG', self)
        self.gbx_emg.setObjectName('GroupBoxEmg')
        self.gbx_emg.setGeometry(QRect(10, 10, 1020, 840))

        wdg_emg = QWidget(self.gbx_emg)
        wdg_emg.setObjectName('WidgetEmg')
        wdg_emg.setGeometry(QRect(10, 30, 1000, 800))

        layout_emg = QVBoxLayout(wdg_emg)
        layout_emg.setObjectName('LayoutPlotEmg')
        layout_emg.setContentsMargins(0, 0, 0, 0)

        self.plot_emgs  = list()
        self.curve_emgs = list()

        for i in range(8):
            pwg = PlotWidget(name='PlotEmg')
            pwg.setXRange(0, self.sample_displayed)
            pwg.setYRange(-600, 600)
            # pwg.setAspectLocked(True)
            self.plot_emgs.append(pwg.plot(pen='y'))
            self.curve_emgs.append(deque(self.sample_displayed * [0], maxlen=self.sample_displayed))
            self.plot_emgs[-1].setData(self.curve_emgs[-1])
            layout_emg.addWidget(pwg)

    def _init_ui_status(self) -> None:
        self.gbx_status = QGroupBox('Status', self)
        self.gbx_status.setObjectName('GroupBoxStatus')
        self.gbx_status.setGeometry(QRect(1040, 10, 280, 80))

        wdg_status = QWidget(self.gbx_status)
        wdg_status.setObjectName('WidgetStatus')
        wdg_status.setGeometry(QRect(10, 20, 260, 50))

        layout_status = QGridLayout()
        layout_status.setObjectName('LayoutStatus')
        layout_status.setContentsMargins(0, 0, 0, 0)

        self.lbl_rssi_0 = QLabel(text='RSSI')
        self.lbl_rssi_0.setObjectName('LabelRssi')

        self.lbl_rssi_1 = QLabel(text='')
        self.lbl_rssi_1.setObjectName('LabelRssiSatus')

        self.lbl_battery_0 = QLabel(text='Battery')
        self.lbl_battery_0.setObjectName('LabelBattery')

        self.lbl_battery_1 = QLabel(text='')
        self.lbl_battery_1.setObjectName('LabelBatterySatus')

        layout_status.addWidget(self.lbl_rssi_0, 0, 0, 1, 1)
        layout_status.addWidget(self.lbl_rssi_1, 0, 1, 1, 1)
        layout_status.addWidget(self.lbl_battery_0, 1, 0, 1, 1)
        layout_status.addWidget(self.lbl_battery_1, 1, 1, 1, 1)

        wdg_status.setLayout(layout_status)

    def _init_ui_directory(self) -> None:
        font = QFont()
        font.setPointSize(10)

        self.gbx_directory = QGroupBox('Directory', self)
        self.gbx_directory.setObjectName('GroupBoxDirectory')
        self.gbx_directory.setGeometry(QRect(1040, 100, 280, 120))

        self.btn_dir = QPushButton(self.gbx_directory, text='Browse')
        self.btn_dir.setObjectName('ButtonDirectory')
        self.btn_dir.setGeometry(QRect(10, 30, 80, 35))

        self.lbl_dir = QLabel(self.gbx_directory, text=self._dir)
        self.lbl_dir.setObjectName('LabelDirectory')
        self.lbl_dir.setGeometry(QRect(10, 75, 260, 60))
        self.lbl_dir.setLocale(QLocale(QLocale.English, QLocale.Taiwan))
        self.lbl_dir.setAlignment(Qt.AlignLeading | Qt.AlignLeft | Qt.AlignTop)
        self.lbl_dir.setFont(font)
        self.lbl_dir.setWordWrap(True)

    def _init_ui_file(self) -> None:
        self.gbx_file = QGroupBox('File Name', self)
        self.gbx_file.setObjectName('GroupBoxFile')
        self.gbx_file.setGeometry(QRect(1040, 230, 280, 110))

        self.lbl_gesture = QLabel(self.gbx_file, text='Gesture Name')
        self.lbl_gesture.setObjectName('LabelGesture')
        self.lbl_gesture.setGeometry(QRect(10, 30, 100, 30))

        self.lne_gesture = QLineEdit(self.gbx_file)
        self.lne_gesture.setObjectName('LineEditGesture')
        self.lne_gesture.setGeometry(QRect(10, 65, 100, 30))
        self.lne_gesture.setText(self.gesture)

        self.lbl_repetition = QLabel(self.gbx_file, text='Repetition')
        self.lbl_repetition.setObjectName('LabelRepetition')
        self.lbl_repetition.setGeometry(QRect(160, 30, 100, 30))

        self.lne_repetition = QLineEdit(self.gbx_file)
        self.lne_repetition.setObjectName('LineEditRepetition')
        self.lne_repetition.setGeometry(QRect(160, 65, 100, 30))
        self.lne_repetition.setText(str(self.repetition))

    def _init_ui_discover(self) -> None:
        self.gbx_discover = QGroupBox('Discover Device', self)
        self.gbx_discover.setObjectName('GroupBoxFile')
        self.gbx_discover.setGeometry(QRect(1040, 350, 280, 100))

        wdg_discover = QWidget(self.gbx_discover)
        wdg_discover.setObjectName('WidgetDiscover')
        wdg_discover.setGeometry(QRect(10, 30, 260, 60))

        layout_discover = QVBoxLayout()
        layout_discover.setObjectName('LayoutDiscover')
        layout_discover.setContentsMargins(0, 0, 0, 0)

        self.btn_discover = QPushButton('Discover')
        self.setObjectName('ButtonDiscover')

        self.cbx_device = QComboBox()
        self.cbx_device.setObjectName('ComboBoxDevice')

        layout_discover.addWidget(self.btn_discover)
        layout_discover.addWidget(self.cbx_device)
        wdg_discover.setLayout(layout_discover)

    def _init_ui_button(self):
        self.gbx_button = QGroupBox(parent=self)
        self.gbx_button.setObjectName('GroupBoxFunction')
        self.gbx_button.setGeometry(QRect(1040, 460, 280, 155))

        wdg_button = QWidget(self.gbx_button)
        wdg_button.setObjectName('WidgetButton')
        wdg_button.setGeometry(QRect(10, 10, 260, 140))

        layout_button = QVBoxLayout()
        layout_button.setObjectName('LayoutButton')
        layout_button.setContentsMargins(0, 0, 0, 0)

        self.btn_conn = QPushButton('Connect')
        self.btn_conn.setObjectName('ButtonConnect')

        self.btn_disconn = QPushButton('Disconnect')
        self.btn_disconn.setObjectName('ButtonDisconnect')

        self.btn_start = QPushButton('Start')
        self.btn_start.setObjectName('ButtonStart')

        self.btn_save = QPushButton('Save')
        self.btn_save.setObjectName('ButtonSave')

        layout_button.addWidget(self.btn_conn)
        layout_button.addWidget(self.btn_disconn)
        layout_button.addWidget(self.btn_start)
        layout_button.addWidget(self.btn_save)
        wdg_button.setLayout(layout_button)

    def _init_ui_console(self):
        font = QFont()
        font.setPointSize(8)

        self.gbx_console = QGroupBox(self)
        self.gbx_console.setObjectName('GroupBoxConsole')
        self.gbx_console.setGeometry(QRect(1040, 620, 280, 230))

        self.tbr_console = QTextBrowser(self.gbx_console)
        self.tbr_console.setObjectName('TextBrowserConsole')
        self.tbr_console.setGeometry(QRect(5, 10, 270, 215))
        self.tbr_console.setLocale(QLocale(QLocale.English, QLocale.Taiwan))
        self.tbr_console.setFont(font)

    @Slot(bool)
    def receive_connected(self, connected: bool) -> None:
        self._connected = connected

    @Slot(tuple)
    def receive_raw_emg(self, data_raw_emg: tuple):
        self._update_recording_file(data_raw_emg)
        self._update_plot_emg(data_raw_emg)

    def _setup_recording_file(self) -> None:
        path = Path(self._dir)
        if not path.exists():
            self.tbr_console.append(f'Saving directory does not exist! Creating director: {str(self._dir)}...')
            path.mkdir(parents=True, exist_ok=True)
            self.tbr_console.append('Finished creating directory!')
        self.filename = f'{self.gesture}_{self.repetition}.csv'
        with open(str(path / self.filename), 'w') as f:
            f.write(','.join([f'channel{i}' for i in range(8)]))

    def _update_plot_emg(self, data_raw_emg: tuple) -> None:
        for i in range(8):
            self.curve_emgs[i].appendleft(data_raw_emg[0][i])
            self.curve_emgs[i].appendleft(data_raw_emg[1][i])
            self.plot_emgs[i].setData(self.curve_emgs[i])
        time.sleep(0.002)

    def _update_recording_file(self, data_raw_emg: tuple) -> None:
        try:
            with open(str(Path(self._dir) / self.filename), 'a') as f:
                f.write('\n' + ','.join([str(emg) for emg in data_raw_emg[0]]))
                f.write('\n' + ','.join([str(emg) for emg in data_raw_emg[1]]))
        except IOError:
            self.tbr_console.append(f'Failed recording file!')

    async def _init_device(self, address: str) -> None:
        if isinstance(self._myo, QMyo):
            if self._connected:
                await self._myo.disconnect_device()
        loop_myo = asyncio.get_event_loop()
        self._myo = QMyo(loop_myo)
        self._myo.signal_connected.connect(self.receive_connected)
        self.signal_streamed.connect(self._myo.receive_streamed)
        await self._myo.connect_device(address)

    def handle_directory(self) -> None:
        self._dir = QFileDialog.getExistingDirectory(self, 'Select location for save', './')
        self.lbl_dir.setText(self._dir)

    @asyncSlot()
    async def handle_discover(self) -> None:
        self.tbr_console.append('Started discover...')
        devices = await BleakScanner.discover()
        self.cbx_device.clear()
        for i, device in enumerate(devices):
            self.cbx_device.insertItem(i, device.name, device)
        self.tbr_console.append('Finnish discovered!')

    @asyncSlot()
    async def handle_connect(self) -> None:
        # activate/deactivate some buttons and text boxes
        self.btn_dir.setEnabled(False)
        self.btn_discover.setEnabled(False)
        #
        self.cbx_device.setEnabled(False)
        #
        self.lne_gesture.setEnabled(False)
        self.lne_repetition.setEnabled(False)

        # try connecting the selected device
        self.tbr_console.append('Try connecting...')
        device = self.cbx_device.currentData()
        if isinstance(device, BLEDevice):
            await self._init_device(device.address)
        else:
            self.tbr_console.append(f'Actually not bluetooth device! Try discovering devices')

            # activate/deactivate some buttons and text boxes
            self.btn_dir.setEnabled(True)
            self.btn_discover.setEnabled(True)
            #
            self.cbx_device.setEnabled(True)
            #
            self.lne_gesture.setEnabled(True)
            self.lne_repetition.setEnabled(True)

        print(self._connected)

        if self._connected:
            self.tbr_console.append('Connected!')

            # activate/deactivate some buttons and text boxes
            self.btn_conn.setEnabled(False)
            self.btn_disconn.setEnabled(True)
            self.btn_start.setEnabled(True)
            self.btn_save.setEnabled(True)
        else:
            self.tbr_console.append(f'Cannot connect the device!')

            # activate/deactivate some buttons and text boxes
            self.btn_dir.setEnabled(True)
            self.btn_discover.setEnabled(True)
            #
            self.cbx_device.setEnabled(True)
            #
            self.lne_gesture.setEnabled(True)
            self.lne_repetition.setEnabled(True)

    @asyncSlot()
    async def handle_disconnect(self) -> None:
        # try disconnecting the connected device
        self.tbr_console.append('Disconnect device...')

        # un-streaming EMG data
        if self._streamed:
            self._streamed = False
            self.signal_streamed.emit(self._streamed)

        if isinstance(self._myo, QMyo):
            await self._myo.disconnect_device()
        else:
            self.tbr_console.append(f'No connected bluetooth device! Try discovering devices')

            # activate/deactivate some buttons and text boxes
            self.btn_dir.setEnabled(True)
            self.btn_discover.setEnabled(True)
            self.btn_conn.setEnabled(True)
            self.btn_disconn.setEnabled(False)
            self.btn_start.setEnabled(False)
            self.btn_save.setEnabled(False)
            #
            self.cbx_device.setEnabled(True)
            #
            self.lne_gesture.setEnabled(True)
            self.lne_repetition.setEnabled(True)

        print(self._connected)

        if not self._connected:
            self.tbr_console.append('Disconnected!')

            # activate/deactivate some buttons and text boxes
            self.btn_dir.setEnabled(True)
            self.btn_discover.setEnabled(True)
            self.btn_conn.setEnabled(True)
            self.btn_disconn.setEnabled(False)
            self.btn_start.setEnabled(False)
            self.btn_save.setEnabled(False)
            #
            self.cbx_device.setEnabled(True)
            #
            self.lne_gesture.setEnabled(True)
            self.lne_repetition.setEnabled(True)
        else:
            self.tbr_console.append('Try disconnecting again!')

    def handle_start(self) -> None:
        self.tbr_console.append(f'Start recording...')

        # setup recording file
        self._setup_recording_file()

        # send streaming signal
        if not self._streamed:
            self._streamed = True
            self.signal_streamed.emit(self._streamed)

        # start stream EMG data
        if not self.first_start:
            self._myo.signal_raw_emg.connect(self.receive_raw_emg)
            self._myo.ensure_stream_raw_emg()
            self.first_start = True

        # activate/deactivate some buttons and text boxes
        self.btn_dir.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_save.setEnabled(True)
        #
        self.lne_gesture.setEnabled(False)
        self.lne_repetition.setEnabled(False)

        self.tbr_console.append('Recording!')

    @asyncSlot()
    async def handle_save(self):
        self.tbr_console.append(f'Stop recording and save file...')
        if self._streamed:
            self._streamed = False
            self.signal_streamed.emit(self._streamed)

        # print(self._streamed)

        # reset plots
        del self.curve_emgs
        gc.collect()
        self.curve_emgs = list()
        for i in range(8):
            self.curve_emgs.append(deque(self.sample_displayed * [0], maxlen=self.sample_displayed))
            self.plot_emgs[i].setData(self.curve_emgs[-1])

        # activate/deactivate some buttons and text boxes
        self.btn_dir.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.btn_save.setEnabled(False)
        #
        self.lne_gesture.setEnabled(True)
        self.lne_repetition.setEnabled(True)

        self.tbr_console.append('Stopped!')

    def handle_editingfinished_gesture(self) -> None:
        self.gesture = self.lne_gesture.text()

    def handle_editingfinished_repetition(self) -> None:
        if self.lne_repetition.text().isnumeric():
            self.repetition = int(self.lne_repetition.text())
        else:
            QMessageBox.question(self,
                                 'Message',
                                 'The repetition should be a number!',
                                 buttons=QMessageBox.Ok,
                                 defaultButton=QMessageBox.Ok)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._streamed or self._connected:
            reply = QMessageBox.question(self,
                                         'Message',
                                         'Please disconnect Myo device before closing!',
                                         buttons=QMessageBox.Ok,
                                         defaultButton=QMessageBox.Ok)
            if reply == QMessageBox.Ok:
                event.ignore()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()
