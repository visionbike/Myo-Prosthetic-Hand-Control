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

from typing import Union, Optional, Type, Callable, Any
import struct
import asyncio
import bleak
from async_property import async_property
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic, UUID
from PySide6.QtCore import QObject, Signal, Slot
from .defines import *

__all__ = ['QMyo']


class QMyo(QObject):
    signal_connected = Signal(bool)
    signal_raw_emg   = Signal(tuple)

    def __init__(self, loop: asyncio.AbstractEventLoop, parent: QObject = None) -> None:
        """

        :param loop: the loop event
        :param parent: the parent widget
        """

        super(QMyo, self).__init__(parent)

        self._reset()
        self._loop = loop
        self._handle_raw_emgs = [NotifHandle.EMG_0, NotifHandle.EMG_1, NotifHandle.EMG_2, NotifHandle.EMG_3]
        self._handle_filt_emgs = [NotifHandle.EMG_PROC, NotifHandle.EMG_0, NotifHandle.EMG_1, NotifHandle.EMG_2, NotifHandle.EMG_3]
        self._handle_imu = [NotifHandle.IMU]

    def _reset(self) -> None:
        """
        Reset attributes of Myo device

        :return:
        """

        self._name             = ''
        self._basic_info       = BasicInfo
        self._firmware_version = FirmwareVersion

        self._queue_raw_emg  = asyncio.Queue()
        self._queue_filt_emg = asyncio.Queue()
        self._queue_imu      = asyncio.Queue()

        self._data_raw_emg  = tuple()
        self._data_filt_emg = tuple()

        self._device    = None
        self._connected = False
        self._streamed  = False
        self._loop      = None

    @Slot(bool)
    def receive_streamed(self, streamed: bool) -> None:
        """
        Receive streaming signal from the main GUI
        :param streamed: whether to send data or not.
        :return:
        """

        self._streamed = streamed

    async def _run_command(self, data: Union[bytes, bytearray, memoryview]) -> None:
        """
        Run command based on the specific GATT characteristic

        :param data: data to send
        :return:
        """

        await self._device.write_gatt_char(InfoHandle.COMMAND, data)

    async def _read_data(self, char_specifier: Union[BleakGATTCharacteristic, int, str, UUID]) -> bytearray:
        """
        Read on the specific GATT characteristic

        :param char_specifier: the characteristic to read from
        :return:
        """

        return await self._device.read_gatt_char(char_specifier)

    async def _start_subscription(self, handles: list[int], callback: Optional[Callable[..., Any]] = None) -> None:
        """
        Activate notifications/indications on a characteristic

        :param handles: a list of handles
        :param callback: callback function
        :return:
        """

        if callback is None:
            def callback(sender: int, data: bytearray):
                print(f'{sender}: {data}')

        for handle in handles:
            await self._device.start_notify(handle, callback)

    async def _stop_subscription(self, handles: list[int]) -> None:
        """
        Deactivate notifications/indications on a characteristic

        :param handles: a list og handles
        :return:
        """

        for handle in handles:
            await self._device.stop_notify(handle)

    async def _callback_raw_emg(self, sender: int, data: bytearray) -> None:
        """
        Callback function to get raw EMG data

        :param sender: the handle to send
        :param data: the data
        :return:
        """

        if sender not in [NotifHandle.EMG_0, NotifHandle.EMG_1, NotifHandle.EMG_2, NotifHandle.EMG_3]:
            raise ValueError(f'Incorrect raw EMG handles. Got {sender} handle.')

        idx = 0
        if sender == NotifHandle.EMG_0:
            idx = 0
        elif sender == NotifHandle.EMG_1:
            idx = 1
        elif sender == NotifHandle.EMG_2:
            idx = 2
        elif sender == NotifHandle.EMG_3:
            idx = 3

        emg = struct.unpack('<16b', data)
        await self._queue_raw_emg.put((idx, emg))

    async def _callback_filt_emg(self, sender: int, data: bytearray) -> None:
        """
        Callback function to get filtered EMG data

        :param sender: the handle to send
        :param data: the data
        :return:
        """

        if sender not in [NotifHandle.EMG_PROC, NotifHandle.EMG_0, NotifHandle.EMG_1, NotifHandle.EMG_2, NotifHandle.EMG_3]:
            raise ValueError(f'Incorrect filtered EMG handles. Got {sender} handle.')

        idx = 0
        if sender == NotifHandle.EMG_0:
            idx = 0
        elif sender == NotifHandle.EMG_1:
            idx = 1
        elif sender == NotifHandle.EMG_2:
            idx = 2
        elif sender == NotifHandle.EMG_3:
            idx = 3

        emg = struct.unpack('<8H', data)
        await self._queue_filt_emg.put((idx, emg))

    async def connect_device(self, address: str, **kwargs) -> None:
        """
        Connect to Myo device

        :param address: the MAC address
        :param kwargs:
        :return:
        """

        # init BleakClient and connect Myo device
        try:
            if not self._connected:
                self._device = BleakClient(address, **kwargs)
                await self._device.connect()

                self._connected = True
        except bleak.exc.BleakError:
            self._connected = False

        # get basic information from Myo device
        await self.read_device_name()
        await self.read_basic_info()
        await self.read_firmware_version()
        await self.set_sleep_mode(SleepMode.NEVER_SLEEP)
        # set vibration
        await self.vibrate(VibrationMode.LONG)

        self.signal_connected.emit(self._connected)

    async def disconnect_device(self) -> None:
        """
        Disconnect to Myo device

        :return:
        """
        try:
            if self._connected:
                await self.vibrate(VibrationMode.LONG)
                await self._device.disconnect()

                self._connected = False
        except bleak.exc.BleakError:
            self._connected = True

        self._reset()

        self.signal_connected.emit(self._connected)

    async def set_mode(self, emg_mode=EmgMode.RAW, imu_mode=ImuMode.NONE, clf_mode=ClassifierMode.DISABLED) -> None:
        """
        Set EMyo recording mode

        :param emg_mode: the emg mode. Default: `EmgMode.Raw`
        :param imu_mode: the imu mode Default: `ImuMode.None`
        :param clf_mode: the classifier mode. `ClassifierMode.DISABLED`
        :return:
        """

        # set Myo recording mode
        command = struct.pack('<5B', CommandHandle.SET_MODE, 3, emg_mode, imu_mode, clf_mode)
        await self._run_command(command)

    async def vibrate(self, vibrate_mode: VibrationMode.SHORT) -> None:
        """
        Set Myo vibration

        :param vibrate_mode: the vibration value. Default: `VibrationMode.SHORT`
        :return:
        """

        command = struct.pack('<3B', CommandHandle.VIBRATE, 1, vibrate_mode)
        await self._run_command(command)

    async def deep_sleep(self) -> None:
        """
        Deep sleep command.
        If you send this command, the Myo armband will go into a deep sleep with everything basically off.
        It can stay in this state for months (indeed, this is the state the Myo armband ships in),
        but the only way to wake it back up is by plugging it in via USB.
        (source: https://developerblog.myo.com/myo-bluetooth-spec-released/)

        Note
        ----
        Don't send this command lightly, a user may not know what happened or have the knowledge/ability to recover.

        :return:
        """

        await self._run_command(b'\x04\x00')

    async def set_led_color(self, rgb_logo: tuple[int, int, int], rgb_line: tuple[int, int, int]) -> None:
        """
        Set color for LED logos

        :param rgb_logo: the rgb value for logo
        :param rgb_line: the rgb value for bar
        :return:
        """

        await self._run_command(struct.pack('<8B', CommandHandle.SET_LED, 6, *rgb_logo, *rgb_line))

    async def vibrate2(self, steps: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]) -> None:
        """
        Set Myo vibration (extension)

        :param steps: 6 vibration steps
        :return:
        """

        command = struct.pack('<2B' + 6 * 'HB', CommandHandle.VIBRATE2, 20, *sum(steps, ()))
        await self._run_command(command)

    async def set_sleep_mode(self, sleep_mode: SleepMode.NEVER_SLEEP) -> None:
        """
        Set Myo sleep mode

        :param sleep_mode: the sleep mode value. Default: `SleepMode.NEVER_SLEEP`
        :return:
        """

        command = struct.pack('<3B', CommandHandle.SET_SLEEP_MODE, 1, sleep_mode)
        await self._run_command(command)

    async def unlock_device(self, unlock_mode: UnlockMode = UnlockMode.HOLD) -> None:
        """
        Set Myo unlock mode

        :param unlock_mode: the unlock mode value. Default: `UnlockMode.HOLD`
        :return:
        """

        command = struct.pack('<3B', CommandHandle.UNLOCK, 1, unlock_mode)
        await self._run_command(command)

    async def user_action(self, user_mode: UserActionMode.SINGLE) -> None:
        """
        Set Myo user action mode

        :param user_mode: the user action mode value. Default: `UserActionMode.SINGLE`
        :return:
        """

        command = struct.pack('<3B', CommandHandle.USER_ACTION, 1, user_mode)
        await self._run_command(command)

    async def read_device_name(self) -> None:
        """
        Read device name

        :return:
        """

        self._name = (await self._read_data('00002a00-0000-1000-8000-00805f9b34fb')).decode()

    async def read_basic_info(self) -> None:
        """
        Read basic information of Myo device

        :return:
        """

        data = await self._read_data(InfoHandle.INFO)
        info = struct.unpack('<6sH5B7x', data)

        self._basic_info = BasicInfo(serial_number=info[0],
                                     unlock_pose=Pose(info[1]),
                                     classifier_type=ClassifierMode(info[2]),
                                     classifier_index=info[3],
                                     has_custom_classifier=bool(info[4]),
                                     stream_indicating=bool(info[5]),
                                     sku=SKU(info[6]))

    async def read_firmware_version(self) -> None:
        """
        Read firmware version of Myo device

        :return:
        """

        data = await self._read_data(InfoHandle.FIRMWARE)
        firmware = struct.unpack('<4H', data)

        self._firmware_version = FirmwareVersion(major=firmware[0],
                                                 minor=firmware[1],
                                                 patch=firmware[2],
                                                 hardware_rev=HardwareRevision(firmware[3]))

    async def stream_raw_emg(self) -> None:
        """
        Stream raw EMG data

        :return:
        """

        try:
            # print(self._streamed)

            # set device modes
            await self.unlock_device(UnlockMode.HOLD)
            await self.set_mode(EmgMode.RAW)

            # subscribe EMG notifications
            await self._start_subscription(self._handle_raw_emgs, self._callback_raw_emg)

            while self._connected:
                if self._queue_raw_emg.qsize() > 0:
                    char_received, emg = await self._queue_raw_emg.get()
                    self._data_raw_emg = (emg[:8], emg[8:])
                    if self._streamed:
                        # send data when click Start button in GUI
                        self.signal_raw_emg.emit(self._data_raw_emg)
                else:
                    await asyncio.sleep(0.0001)

            await self._stop_subscription(self._handle_raw_emgs)
        except bleak.exc.BleakError:
            self._connected = False

    async def stream_filt_emg(self) -> None:
        """
        Stream filtered EMG data

        :return:
        """

        try:
            # print(self._streamed)

            # set device modes
            await self.unlock_device(UnlockMode.HOLD)
            await self.set_mode(EmgMode.RAW)

            # subscribe EMG notifications
            await self._start_subscription(self._handle_filt_emgs, self._callback_filt_emg)

            while self._connected:
                if self._queue_filt_emg.qsize() > 0:
                    char_received, emg = await self._queue_filt_emg.get()
                    print(emg)
                    # self._data_raw_emg = (emg[:8], emg[8:])
                    if self._streamed:
                        # send data when click Start button in GUI
                        self.signal_raw_emg.emit(self._data_filt_emg)
                else:
                    await asyncio.sleep(0.0001)

            await self._stop_subscription(self._handle_filt_emgs)
        except bleak.exc.BleakError:
            self._connected = False

    def ensure_stream_raw_emg(self):
        self.task = asyncio.ensure_future(self.stream_raw_emg(), loop=self._loop)

    def ensure_stream_filt_emg(self):
        self.task = asyncio.ensure_future(self.stream_filt_emg(), loop=self._loop)

    @async_property
    async def name(self) -> str:
        """
        Myo device name

        :return:
        """

        return self._name

    @async_property
    async def battery(self) -> int:
        """
        Current battery level information

        :return:
        """

        return ord(await self._read_data(InfoHandle.BATTERY))

    @property
    def basic_info(self) -> Type[BasicInfo]:
        """
        Basic information of this Myo

        :return:
        """

        return self._basic_info

    @property
    def firmware_version(self) -> Type[FirmwareVersion]:
        """
        Version information for the Myo firmware

        :return:
        """

        return self._firmware_version
