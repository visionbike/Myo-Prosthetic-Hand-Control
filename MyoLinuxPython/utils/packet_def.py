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

# The BLE specification for Myo armband
# Reference:
# https://github.com/thalmiclabs/myo-bluetooth
# https://github.com/sebastiankmiec/PythonMyoLinux/pymyolinux

import copy

__all__ = [
    'get_full_uuid',
    'HardwareServices',
    'BluetoothMessages',
    'WifiMessages',
    'CommandMessages',
    'PackageMessages',
    'BGAPIClasses',
    'ConnectionResponseCommands',
    'ConnectionEventCommands',
    'GATTResponseCommands',
    'GATTEventCommands',
    'GAPResponseCommands',
    'GAPEventCommands',
    'GATTTransmitCommands',
    'GAPTransmitCommands',
    'NotificationCommands',
    'ConnectionStatus',
    'GAPConnectableModes',
    'GAPDiscoverableModes',
    'GAPDiscoverModes',
    'BleResponseConditions',
    'BleErrorCodes',
    'MyoCommands',
    'EmgModes',
    'ImuModes',
    'ClassifierModes',
    'SleepModes'
]

MYO_SERVICE_BASE_UUID = bytearray(b'\x42\x48\x12\x4a\x7f\x2c\x48\x47\xb9\xde\x04\xa9\x00\x00\x06\xd5')


def get_full_uuid(short_uuid):
    new_uuid = copy.deepcopy(MYO_SERVICE_BASE_UUID)
    new_uuid[12] = short_uuid[1]
    new_uuid[13] = short_uuid[0]
    return new_uuid


class HardwareServices:
    ControlService              = b'\x00\x01'   # Myo info service (advertising packets)

    CommandCharacteristic       = b'\x04\x01'   # only-writen attribute to issue commands (such as setting Myo mode)

    IMUDataCharacteristic       = b'\x04\x02'   # notify-only characteristic for IMU data

    EmgData0Characteristic      = b'\x01\x05'   # raw emg data; notify-only characteristic
    EmgData1Characteristic      = b'\x02\x05'   # raw emg data; notify-only characteristic
    EmgData2Characteristic      = b'\x03\x05'   # raw emg data; notify-only characteristic
    EmgData3Characteristic      = b'\x04\x05'   # raw emg data; notify-only characteristic

    BatteryLevelCharacteristic  = b'\x19\x2a'   # current battery level information; read/notify characteristic; note: the order of bytes


# Bluegiga packet definitions

# message types
class BluetoothMessages:
    bluetooth_resp  = 0x00
    bluetooth_event = 0x80


class WifiMessages:
    wifi_resp  = 0x08
    wifi_event = 0x88


class CommandMessages:
    command_message = 0x00


class PackageMessages:
    packet_header_length    = 4
    packet_type_bits        = 0x88
    packet_length_high_bits = 0x07


class BGAPIClasses:
    Connection = 0x03   # functions to access connection management
    GATT       = 0x04   # functions to access remote devices GATT database
    GAP        = 0x06   # GAP (Generic Access Profile) functions


class ConnectionResponseCommands:
    ble_rsp_connection_disconnect = 0x00    # response


class ConnectionEventCommands:
    ble_evt_connection_status       = 0x00  # event
    ble_evt_connection_disconnected = 0x04  # event


class GATTResponseCommands:
    ble_rsp_gatt_read_by_group_type = 0x01
    ble_rsp_gatt_find_information   = 0x03
    ble_rsp_gatt_attribute_write    = 0x05


class GATTEventCommands:
    ble_evt_gatt_procedure_completed    = 0x01
    ble_evt_gatt_group_found            = 0x02
    ble_evt_gatt_find_information_found = 0x04
    ble_evt_gatt_attribute_value        = 0x05


class GAPEventCommands:
    ble_evt_gap_scan_response = 0x00
    ble_evt_gap_mode_changed  = 0x01


class GAPResponseCommands:
    ble_rsp_gap_set_mode        = 0x01
    ble_rsp_gap_discover        = 0x02
    ble_rsp_gap_connect_direct  = 0x03
    ble_rsp_gap_end_procedure   = 0x04


# Bluegiga packet definitions for transmission

# GATT
class GATTTransmitCommands:
    ble_tmt_connection_disconnect        = 0x00
    ble_tmt_attclient_read_by_group_type = 0x01
    ble_tmt_attclient_find_information   = 0x03
    ble_tmt_attclient_read_by_handle     = 0x04
    ble_tmt_attclient_attribute_write    = 0x05


# GAP
class GAPTransmitCommands:
    ble_tmt_gap_set_mode       = 0x01
    ble_tmt_gap_discover       = 0x02
    ble_tmt_gap_connect_direct = 0x03
    ble_tmt_gap_end_procedure  = 0x04


# BLE command definitions

class NotificationCommands:
    disable_notifications = b'\x00\x00'
    enable_notifications  = b'\x01\x00'


class ConnectionStatus:
    connection_connected         = 1
    connection_encrypted         = 2
    connection_completed         = 4
    connection_parameters_change = 8
    connection_connstatus_max    = 9


class GAPDiscoverableModes:
    gap_non_discoverable      = 0
    gap_limited_discoverable  = 1
    gap_general_discoverable  = 2
    gap_broadcast             = 3
    gap_user_data             = 4
    gap_discoverable_mode_max = 5


class GAPConnectableModes:
    gap_non_connectable        = 0
    gap_directed_connectable   = 1
    gap_undirected_connectable = 2
    gap_scannable_connectable  = 3
    gap_connectable_mode_max   = 4


class GAPDiscoverModes:
    gap_discover_limited     = 0
    gap_discover_generic     = 1
    gap_discover_observation = 2
    gap_discover_mode_max    = 3


# BLE Response Conditions
class BleResponseConditions:
    find_info_success            = 0
    write_success                = 0
    disconnect_procedure_started = 0
    disconnect_due_local_user    = 0
    gap_set_mode_success         = 0
    gap_start_procedure_success  = 0
    gap_end_procedure_success    = 0
    gatt_end_procedure_success   = 0


# Bluetooth error codes
class BleErrorCodes:
    connection_timeout            = 0x0208
    connection_term_by_local_host = 0x0216


# Myo command definitions
class MyoCommands:
    myo_cmd_set_mode       = 0x01   # set EMG and IMU modes
    myo_cmd_vibrate        = 0x03   # vibrate
    myo_cmd_deep_sleep     = 0x04   # put Myo into deep sleep
    myo_cmd_vibrate2       = 0x07   # extended vibrate
    myo_cmd_set_sleep_mode = 0x09   # set sleep mode
    myo_cmd_unlock         = 0x0a   # unlock Myo
    myo_cmd_user_action    = 0x0b   # notify user that an action has been recognized / confirmed


class EmgModes:
    myo_emg_mode_none         = 0x00    # do not send EMG data
    myo_emg_mode_send_emg     = 0x02    # send filtered EMG data
    myo_emg_mode_send_emg_raw = 0x03    # send raw(unfiltered) EMG data


class ImuModes:
    myo_imu_mode_none        = 0x00     # do not send IMU data or events
    myo_imu_mode_send_data   = 0x01     # send IMU data streams (accelerometer, gyroscope, and orientation)
    myo_imu_mode_send_events = 0x02     # send motion events detected by the IMU (e.g. taps)
    myo_imu_mode_send_all    = 0x03     # send both IMU data streams and motion events
    myo_imu_mode_send_raw    = 0x04     # send raw IMU data streams


class ClassifierModes:
    myo_classifier_mode_disabled = 0x00     # disable and reset the internal state of the onboard classifier
    myo_classifier_mode_enabled  = 0x01     # send classifier events (poses and arm events)


class SleepModes:
    myo_sleep_mode_normal      = 0  # normal sleep mode; Myo will sleep after a period of inactivity
    myo_sleep_mode_never_sleep = 1  # never go to sleep
