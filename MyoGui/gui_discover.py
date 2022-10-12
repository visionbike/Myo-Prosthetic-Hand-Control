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

import gc
import sys
import asyncio
from asyncio import AbstractEventLoop
import bleak
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QPushButton, QComboBox, QTextBrowser
from qasync import QEventLoop, asyncSlot
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from qmyo import QMyo


class MainWindow(QMainWindow):
    def __init__(self, loop: AbstractEventLoop):
        super(MainWindow, self).__init__()

        self._device = None
        self._is_connected = False
        self._loop = loop

        self.init_ui()

    def init_ui(self) -> None:
        self.btn_discover = QPushButton('Discover Devices')
        self.btn_conn     = QPushButton('Connect')
        self.btn_disconn  = QPushButton('Disconnect')

        self.cbx_device = QComboBox()
        self.tbr_console = QTextBrowser()

        wdg_container = QWidget()

        layout = QVBoxLayout(wdg_container)
        layout.addWidget(self.btn_discover)
        layout.addWidget(self.btn_conn)
        layout.addWidget(self.btn_disconn)
        layout.addWidget(self.cbx_device)
        layout.addWidget(self.tbr_console)

        self.resize(640, 480)
        self.setCentralWidget(wdg_container)

        self.btn_discover.setEnabled(not self._is_connected)
        self.btn_conn.setEnabled(self._is_connected)
        self.btn_disconn.setEnabled(self._is_connected)

        self.btn_discover.clicked.connect(self.handle_discover)
        self.btn_conn.clicked.connect(self.handle_connect)
        self.btn_disconn.clicked.connect(self.handle_disconnect)

    async def init_device(self, address: str) -> None:
        if self._device is not None:
            await self._device.disconnect_device()
        self._device = QMyo(self._loop)
        await self._device.connect_device(address)

    @asyncSlot()
    async def handle_discover(self) -> None:
        self.tbr_console.append('Started discover...')
        devices = await BleakScanner.discover()
        self.cbx_device.clear()
        for i, device in enumerate(devices):
            self.cbx_device.insertItem(i, device.name, device)
        self.tbr_console.append('Finnish discovered!')

        if not self._is_connected:
            self.btn_conn.setEnabled(not self._is_connected)

    @asyncSlot()
    async def handle_connect(self) -> None:
        self.tbr_console.append('Try connect...')
        device = self.cbx_device.currentData()
        if isinstance(device, BLEDevice):
            try:
                await self.init_device(device.address)
                self.tbr_console.append('Connected!')

                if not self._is_connected:
                    self.btn_discover.setEnabled(self._is_connected)
                    self.btn_conn.setEnabled(self._is_connected)
                    self.cbx_device.setEnabled(self._is_connected)
                    self.btn_disconn.setEnabled(not self._is_connected)
                    self._is_connected = not self._is_connected

            except bleak.BleakError:
                pass

    @asyncSlot()
    async def handle_disconnect(self) -> None:
        self.tbr_console.append('Try disconnect...')
        if self._device is not None:
            try:
                await self._device.disconnect_device()
                self.tbr_console.append('Disconnected!')

                if self._is_connected:
                    self.btn_discover.setEnabled(self._is_connected)
                    self.btn_conn.setEnabled(self._is_connected)
                    self.cbx_device.setEnabled(self._is_connected)
                    self.btn_disconn.setEnabled(not self._is_connected)
                    self._is_connected = not self._is_connected
            except bleak.BleakError:
                pass

            del self._device
            gc.collect()
            self._device = None


if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    w = MainWindow(loop)
    w.show()
    with loop:
        loop.run_forever()
