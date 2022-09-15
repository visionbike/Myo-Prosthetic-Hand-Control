"""
Copyright 2022 Phuc Thanh-Thien Nguyen
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# Myo specific BLE event and response handlers for BlueGigaProtocol
# Reference:
# https://github.com/sebastiankmiec/PythonMyoLinux/pymyolinux

import struct
from utils import *

__all__ = [
    'joint_event_handler',
    'receive_attribute_value',
    'add_myo_device',
    'add_connection',
    'disconnect_device',
    'add_found_service',
    'add_found_attribute',
    'complete_finding_service',
    'empty_handler'
]


def joint_event_handler(emg_list: list,
                        orient_w: float, orient_x: float, orient_y: float, orient_z: float,
                        accel_1: float, accel_2: float, accel_3: float,
                        gyro_1: float, gyro_2: float, gyro_3: float, sample_num: int):

    # Accelerometer values are multiplied by the following constant (and are in units of g)
    MYO_ACCELEROMETER_SCALE = 2048.0

    # Gyroscope values are multiplied by the following constant (and are in units of deg/s)
    MYO_GYROSCOPE_SCALE = 16.0

    # Orientation values are multiplied by the following constant (units of a unit quaternion)
    MYO_ORIENTATION_SCALE = 16384.0

    print('-------------------------------------------------------------------------------------------')
    print((emg_list[0], emg_list[1], emg_list[2], emg_list[3], emg_list[4], emg_list[5], emg_list[6], emg_list[7]))
    print((orient_w / MYO_ORIENTATION_SCALE,
           orient_x / MYO_ORIENTATION_SCALE,
           orient_y / MYO_ORIENTATION_SCALE,
           orient_z / MYO_ORIENTATION_SCALE,
           accel_1 / MYO_ACCELEROMETER_SCALE,
           accel_2 / MYO_ACCELEROMETER_SCALE,
           accel_3 / MYO_ACCELEROMETER_SCALE,
           gyro_1 / MYO_GYROSCOPE_SCALE,
           gyro_2 / MYO_GYROSCOPE_SCALE,
           gyro_3 / MYO_GYROSCOPE_SCALE))


def receive_attribute_value(sender_obj: EventType, connection: int, att_handler: bytes, att_type: int, att_value: bytes):
    """
    BLE response handlers for BlueGigaProtocol

    :param sender_obj:
    :param connection:
    :param att_handler:
    :param att_type:
    :param att_value:
    :return:
    """
    if att_handler == sender_obj.imu_handler:
        # IMU
        orient_w, orient_x, orient_y, orient_z, accel_1, accel_2, accel_3, gyro_1, gyro_2, gyro_3 = struct.unpack('<10h', att_value)

        sender_obj.current_imu_read = dict(orient_w=orient_w, orient_x=orient_x, orient_y=orient_y, orient_z=orient_z,
                                           accel_1=accel_1, accel_2=accel_2, accel_3=accel_3,
                                           gyro_1=gyro_1, gyro_2=gyro_2, gyro_3=gyro_3)

        # trigger IMU event
        sender_obj.imu_event(orient_w=orient_w, orient_x=orient_x, orient_y=orient_y, orient_z=orient_z,
                             accel_1=accel_1, accel_2=accel_2, accel_3=accel_3, gyro_1=gyro_1,
                             gyro_2=gyro_2, gyro_3=gyro_3)
    elif ((att_handler == sender_obj.emg_handler_0) or
          (att_handler == sender_obj.emg_handler_1) or
          (att_handler == sender_obj.emg_handler_2) or
          (att_handler == sender_obj.emg_handler_3)):
        # EMG
        (sample_0_1, sample_0_2, sample_0_3, sample_0_4, sample_0_5, sample_0_6, sample_0_7, sample_0_8,
         sample_1_1, sample_1_2, sample_1_3, sample_1_4, sample_1_5, sample_1_6, sample_1_7, sample_1_8) = struct.unpack('<16b', att_value)

        # trigger two EMG events
        sample_num = 1
        sender_obj.emg_event(
            emg_list=[sample_0_1, sample_0_2, sample_0_3, sample_0_4, sample_0_5, sample_0_6, sample_0_7, sample_0_8],
            sample_num=sample_num
        )

        sample_num = 2
        sender_obj.emg_event(
            emg_list=[sample_1_1, sample_1_2, sample_1_3, sample_1_4, sample_1_5, sample_1_6, sample_1_7, sample_1_8],
            sample_num=sample_num
        )

        # trigger two joint IMU/EMG events:
        sample_num = 1
        sender_obj.joint_emg_imu_event(
            emg_list=[sample_0_1, sample_0_2, sample_0_3, sample_0_4, sample_0_5, sample_0_6, sample_0_7, sample_0_8],
            **sender_obj.current_imu_read,
            sample_num=sample_num
        )

        sample_num = 2
        sender_obj.joint_emg_imu_event(
            emg_list=[sample_1_1, sample_1_2, sample_1_3, sample_1_4, sample_1_5, sample_1_6, sample_1_7, sample_1_8],
            **sender_obj.current_imu_read,
            sample_num=sample_num
        )
    elif att_handler == sender_obj.battery_handler:
        # Battery Level Attribute
        sender_obj.battery_level = ord(att_value)


def add_myo_device(sender_obj: EventType, rssi: int, packet_type: int, address: bytes, address_type: int, bond: int, data: bytes):
    """
    BLE event handlers for BlueGigaProtocol

    :param sender_obj:
    :param rssi:
    :param packet_type:
    :param address:
    :param address_type:
    :param bond:
    :param data:
    :return:
    """

    # check if it is a Myo advertising control service packet
    control_uuid = get_full_uuid(HardwareServices.ControlService)
    if data.endswith(control_uuid):
        myo_connection = dict(address=address, address_type=address_type, rssi=rssi)
        unique = True
        for device in sender_obj.myo_devices:
            # note, device also has "rssi"
            if (myo_connection['address'] == device['address']) and (myo_connection['address_type'] == device['address_type']):
                unique = False
                break
        if unique:
            sender_obj.myo_devices.append(myo_connection)


def add_connection(sender_obj: EventType, connection: int, flags: int, address: bytes, address_type: int, conn_interval: int, timeout: int, latency: int, bonding: int):
    """
    Add connection for found Myo device

    :param sender_obj:
    :param connection:
    :param flags:
    :param address:
    :param address_type:
    :param conn_interval:
    :param timeout:
    :param latency:
    :param bonding:
    :return:
    """

    sender_obj.connection = dict(connection=connection,
                                 flags=flags,
                                 address=address,
                                 address_type=address_type,
                                 conn_interval=conn_interval,
                                 timeout=timeout,
                                 latency=latency,
                                 bonding=bonding)


def disconnect_device(sender_obj: EventType, connection: int, reason: bytes):
    """
    Disconnect found Myo device for some reason

    :param sender_obj:
    :param connection:
    :param reason:
    :return:
    """

    if reason == BleErrorCodes.connection_timeout:
        print(f"Connection \"{connection}\" disconnected due to connection timeout (link supervision timeout has expired). Error Code 0x0208")
    elif reason == BleErrorCodes.connection_term_by_local_host:
        print(f"Connection \"{connection}\" disconnected due to termination by local host (local device terminated the connection). Error Code 0x0216")
    else:
        print(f"Connection \"{connection}\" disconnected due to unknown reason (reason = {reason}).")

    sender_obj.disconnecting = False
    sender_obj.connection = None
    sender_obj.found_services = []
    sender_obj.found_attributes = []


def add_found_service(sender_obj: EventType, connection: int, start: bytes, end: bytes, uuid: bytes):
    """
    Add the found service

    :param sender_obj:
    :param connection:
    :param start:
    :param end:
    :param uuid:
    :return:
    """

    sender_obj.found_services.append(dict(start=start, end=end, uuid=uuid))


def add_found_attribute(sender_obj: EventType, connection: int, chr_handler: bytes, uuid: bytes):
    """
    Add the found attribute

    :param sender_obj:
    :param connection:
    :param chr_handler:
    :param uuid:
    :return:
    """

    sender_obj.found_attributes.append(dict(chr_handler=chr_handler, uuid=uuid))


def complete_finding_service(sender_obj: EventType, connection: int, result: bytes, chr_handler: bytes):
    """
    Complete finding service

    :param sender_obj:
    :param connection:
    :param result:
    :param chr_handler:
    :return:
    """

    if result != BleResponseConditions.gap_end_procedure_success:
        raise RuntimeError(f"Attribute protocol error code returned by remote device (result = {result}).")


def empty_handler(sender_obj, **kwargs):
    pass
