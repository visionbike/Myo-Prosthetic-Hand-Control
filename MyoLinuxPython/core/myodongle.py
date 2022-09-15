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

# Myo Dongle implementation
# Reference:
# https://github.com/sebastiankmiec/PythonMyoLinux/pymyolinux

import struct
from core.bluegiga import BlueGigaProtocol
from utils.packet_def import *

__all__ = ['MyoDongle']


class MyoDongle:
    """
    Represents a single Myo dongle, that leverages the Bluegiga API.
    """
    # connection parameters
    default_latency = 0     # This parameter configures the slave latency. Slave latency defines how many connection intervals a slave device can skip.

    default_timeout = 64    # How long the devices can be out of range before the connection is closed (units of 10ms); Range: 10 - 3200

    # Range: 6 - 3200 (in units of 1.25ms).
    # Note: Lower implies faster data transfer, but potentially less reliable data exchanges.
    default_conn_interval_min   = 6     # Time between consecutive connection events (a connection interval); (E.g. a data exchange before going back to an idle state to save power)
    default_conn_interval_max   = 6

    # GATT parameters
    MIN_HANDLE      = 0x1
    MAX_HANDLE      = 0xffff
    PRIMARY_SERVICE = b'\x00\x28'

    def __init__(self, port):
        """

        :param port: Refers to a path to a character device file, for an usb to BLE controller serial interface; e.g. /dev/ttyACM0
        """
        self.ble = BlueGigaProtocol(port)

        # filled via "discover_primary_services()"
        self.handlers        = {}
        self.imu_enabled    = False
        self.emg_enabled    = False
        self.sleep_disabled = False

    def clear_state(self, timeout=2):
        """
        Disconnects any connected devices, stops any advertising, stops any scanning, and resets Myo armband states.

        :param timeout: Time to wait for responses
        """

        if not (self.ble.connection is None):
            # disable IMU readings
            if self.imu_enabled:
                # unsubscribe
                self.transmit_wait(
                    self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['imu_descriptor'], NotificationCommands.disable_notifications),
                    BlueGigaProtocol.ble_rsp_gatt_attribute_write
                )

                resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
                if not resp_received:
                    raise RuntimeError("GATT procedure (write completion to CCCD) response timed out.")

            # Disable EMG readings
            if self.emg_enabled:
                for emg_num in range(4):
                    self.transmit_wait(
                        self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['emg_descriptor_' + str(emg_num)], NotificationCommands.disable_notifications),
                        BlueGigaProtocol.ble_rsp_gatt_attribute_write
                    )

                    resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
                    if not resp_received:
                        raise RuntimeError(f"GATT procedure (write completion to CCCD, emg {emg_num}) response timed out.")

            if self.imu_enabled or self.emg_enabled:
                mode_command_payload = struct.pack('<5B',
                                                   MyoCommands.myo_cmd_set_mode,
                                                   3,  # Payload size
                                                   EmgModes.myo_emg_mode_none,
                                                   ImuModes.myo_imu_mode_none,
                                                   ClassifierModes.myo_classifier_mode_disabled)

                self.transmit_wait(
                    self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['command_characteristic'], mode_command_payload),
                    BlueGigaProtocol.ble_rsp_gatt_attribute_write
                )

                resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
                if not resp_received:
                    raise RuntimeError("GATT procedure (write completion) response timed out.")

            if self.sleep_disabled:
                sleep_mode           = SleepModes.myo_sleep_mode_normal
                mode_command_payload = struct.pack('<3B',
                                                   MyoCommands.myo_cmd_set_sleep_mode,
                                                   1,  # Payload size
                                                   sleep_mode)

                self.transmit_wait(
                    self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['command_characteristic'], mode_command_payload),
                    BlueGigaProtocol.ble_rsp_gatt_attribute_write
                )

                resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
                if not resp_received:
                    raise RuntimeError("GATT procedure (write completion) response timed out.")

        self.emg_enabled    = False
        self.imu_enabled    = False
        self.sleep_disabled = False

        # Disable dongle advertisement
        self.transmit_wait(
            self.ble.ble_cmd_gap_set_mode(GAPDiscoverableModes.gap_non_discoverable, GAPConnectableModes.gap_non_connectable),
            BlueGigaProtocol.ble_rsp_gap_set_mode
        )

        # Disconnect any connected devices
        max_num_connections = 8
        for i in range(max_num_connections):
            self.transmit_wait(
                self.ble.ble_cmd_connection_disconnect(i),
                BlueGigaProtocol.ble_rsp_connection_disconnect
            )

            if self.ble.disconnecting:
                # Need to wait for disconnect response
                resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_connection_disconnected, timeout)
                if not resp_received:
                    raise RuntimeError("Disconnect response timed out.")

        # Stop scanning
        self.transmit_wait(self.ble.ble_cmd_gap_end_procedure(), BlueGigaProtocol.ble_rsp_gap_end_procedure)
        self.handlers = {}

    def discover_myo_devices(self, timeout=2):
        """
        Finds all available Myo armband devices, in terms of MAC address, and rssi.

        :param timeout: Time to wait for responses
        :return: [list] Myo devices found
        """

        # Scan for advertising packets
        self.transmit_wait(
            self.ble.ble_cmd_gap_discover(GAPDiscoverModes.gap_discover_observation),
            BlueGigaProtocol.ble_rsp_gap_discover
        )
        self.ble.read_packets(timeout)

        # Stop scanning
        self.transmit_wait(
            self.ble.ble_cmd_gap_end_procedure(),
            BlueGigaProtocol.ble_rsp_gap_end_procedure
        )

        return self.ble.myo_devices

    def connect(self, myo_device_found, timeout: int = 2):
        """
        Attempt to connect to Myo device, necessary to call other functions (but discover_myo_devices/clear_state).

        :param myo_device_found: A myo device found via discover_myo_devices().
        :param timeout: Time to wait for responses
        :return: [bool] Connection success
        """

        if self.ble.connection is not None:
            raise RuntimeError("BLE connection is not None.")

        # Attempt to connect
        self.transmit_wait(
            self.ble.ble_cmd_gap_connect_direct(myo_device_found['address'],
                                                myo_device_found['address_type'],
                                                self.default_conn_interval_min,
                                                self.default_conn_interval_max,
                                                self.default_timeout,
                                                self.default_latency),
            BlueGigaProtocol.ble_rsp_gap_connect_direct
        )

        # Need to wait for connection response
        resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_connection_status, timeout)
        if not resp_received:
            return False
        return True

    def discover_primary_services(self, timeout: int = 10):
        """
        This function finds all available primary services (and their corresponding ranges) available from the Myo device. This is later used to fill self.handlers.

        :param timeout: Time to wait for responses
        """

        if self.ble.connection is None:
            raise RuntimeError("BLE connection is None.")

        # Find primary service groups
        self.transmit_wait(
            self.ble.ble_cmd_attclient_read_by_group_type(self.ble.connection['connection'],
                                                          self.MIN_HANDLE,
                                                          self.MAX_HANDLE,
                                                          self.PRIMARY_SERVICE),
            BlueGigaProtocol.ble_rsp_gatt_read_by_group_type
        )

        resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed, timeout)
        if not resp_received:
            raise RuntimeError("GATT procedure completion response timed out.")

        for service in self.ble.found_services:
            # For each service group:
            # -> Find available attributes
            self.transmit_wait(
                self.ble.ble_cmd_attclient_find_information(self.ble.connection['connection'],
                                                            service['start'],
                                                            service['end']),
                BlueGigaProtocol.ble_rsp_gatt_find_information
            )

            resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed, timeout)
            if not resp_received:
                raise RuntimeError("GATT procedure completion response timed out.")

    def transmit(self, packet_contents):
        self.ble.transmit_packet(packet_contents)

    def transmit_wait(self, packet_contents, event, timeout: int = 2):
        """
        Send a packet and wait for expected response (every transmitted packet has an expected response)

        :param packet_contents: A bytes object containing packet contents
        :param event: An event to wait for
        :param timeout: Time to wait for aforesaid event
        """

        self.ble.transmit_packet(packet_contents)
        resp_received = self.ble.read_packets_conditional(event, timeout)
        if not resp_received:
            raise RuntimeError("Response timed out for the transmitted command.")

    def add_imu_handler(self, handler):
        """
        On receiving an IMU data packet

        :param handler: A function to be called with the following signature:
        """
        if not self.imu_enabled:
            raise RuntimeError("IMU readings are not enabled.")
        self.ble.imu_event += handler

    def enable_imu_readings(self, timeout: int = 2):
        """
        Enable incoming IMU data packets from Myo device
        """
        if self.ble.connection is None:
            raise RuntimeError("BLE connection is None.")

        # ensure handlers have been discovered
        self.check_handlers()

        self.transmit_wait(
            self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['imu_descriptor'], NotificationCommands.enable_notifications),
            BlueGigaProtocol.ble_rsp_gatt_attribute_write
        )

        resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
        if not resp_received:
            raise RuntimeError("GATT procedure (write completion to CCCD) response timed out.")

        # need to go one step further, by issuing a command to set "Myo device mode"
        emg_mode = EmgModes.myo_emg_mode_send_emg if self.emg_enabled else EmgModes.myo_emg_mode_none

        mode_command_payload    = struct.pack('<5B',
                                              MyoCommands.myo_cmd_set_mode,
                                              3,  # Payload size
                                              emg_mode,
                                              ImuModes.myo_imu_mode_send_data,
                                              ClassifierModes.myo_classifier_mode_disabled)

        self.transmit_wait(
            self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['command_characteristic'], mode_command_payload),
            BlueGigaProtocol.ble_rsp_gatt_attribute_write
        )

        resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
        if not resp_received:
            raise RuntimeError("GATT procedure (write completion) response timed out.")

        self.imu_enabled = True

    def add_emg_handler(self, handler):
        """
        :param handler: A function with an appropriate signature to be called on incoming EMG data packets
        """

        if not self.emg_enabled:
            raise RuntimeError("EMG readings are not enabled.")
        self.ble.emg_event += handler

    def enable_emg_readings(self):
        """
        Enable incoming EMG data packets from Myo device.
        """
        if self.ble.connection is None:
            raise RuntimeError("BLE connection is None.")

        # ensure handlers have been discovered
        self.check_handlers()

        for emg_num in range(4):
            self.transmit_wait(
                self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['emg_descriptor_' + str(emg_num)], NotificationCommands.enable_notifications),
                BlueGigaProtocol.ble_rsp_gatt_attribute_write
            )

            resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
            if not resp_received:
                raise RuntimeError(f"GATT procedure (write completion to CCCD, emg {emg_num}) response timed out.")

        # need to go one step further, by issuing a command to set "Myo device mode"
        imu_mode = ImuModes.myo_imu_mode_send_data if self.imu_enabled else ImuModes.myo_imu_mode_none

        mode_command_payload = struct.pack('<5B',
                                           MyoCommands.myo_cmd_set_mode,
                                           3,  # Payload size
                                           EmgModes.myo_emg_mode_send_emg,
                                           imu_mode,
                                           ClassifierModes.myo_classifier_mode_disabled)

        self.transmit_wait(
            self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['command_characteristic'], mode_command_payload),
            BlueGigaProtocol.ble_rsp_gatt_attribute_write
        )

        resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
        if not resp_received:
            raise RuntimeError("GATT procedure (write completion) response timed out.")

        self.emg_enabled = True

    def add_joint_emg_imu_handler(self, handler):
        """

        :param handler: A function with an appropriate signature to be called on incoming EMG & IMU data packets
        """

        if not self.imu_enabled:
            raise RuntimeError("IMU readings are not enabled.")
        if not self.emg_enabled:
            raise RuntimeError("EMG readings are not enabled.")
        self.ble.joint_emg_imu_event += handler

    def read_battery_level(self):
        """
        Read the battery level of a Myo device.

        :return: [int] battery level (None if not available)
        """

        if self.ble.connection is None:
            raise RuntimeError("BLE connection is None.")

        # ensure handlers have been discovered
        self.check_handlers()

        # issue a command to read Myo device battery level
        self.transmit_wait(
            self.ble.ble_cmd_attclient_read_by_handle(self.ble.connection['connection'], self.ble.battery_handler),
            BlueGigaProtocol.ble_evt_gatt_attribute_value
        )

        return self.ble.battery_level

    def set_sleep_mode(self, device_can_sleep):
        """

        :param device_can_sleep: [bool] True: normal sleep mode / False: no sleep mode
        """
        if self.ble.connection is None:
            raise RuntimeError("BLE connection is None.")

        # ensure handlers have been discovered
        self.check_handlers()

        # issue a command to set "Myo device sleep mode"
        sleep_mode = SleepModes.myo_sleep_mode_normal if device_can_sleep else SleepModes.myo_sleep_mode_never_sleep

        mode_command_payload = struct.pack('<3B',
                                           MyoCommands.myo_cmd_set_sleep_mode,
                                           1,  # Payload size
                                           sleep_mode)

        self.transmit_wait(
            self.ble.ble_cmd_attclient_attribute_write(self.ble.connection['connection'], self.handlers['command_characteristic'], mode_command_payload),
            BlueGigaProtocol.ble_rsp_gatt_attribute_write
        )

        resp_received = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_gatt_procedure_completed)
        if not resp_received:
            raise RuntimeError("GATT procedure (write completion) response timed out.")

        self.sleep_disabled = not device_can_sleep

    def scan_for_data_packets(self, time=10):
        """
        Read incoming packets and trigger relevant events, until a disconnect occurs or time is up.

        :param time: Time to read incoming packets
        """
        self.ble.read_packets(time)

    def scan_for_data_packets_conditional(self, time=10):
        """
        Read incoming packets and trigger relevant events, until a disconnect occurs or time is up.

        :param time: Time to read incoming packets
        :return: [bool] Did a disconnect occur
        """
        disconnect_occurred = self.ble.read_packets_conditional(BlueGigaProtocol.ble_evt_connection_disconnected, time)
        return disconnect_occurred

    def check_handlers(self):
        """
        Ensures all key handlers have been found.
        """

        # need to be able to activate notifications via writing to descriptor handlers
        if len(self.handlers.keys()) == 0:
            self.discover_primary_services()
            if len(self.ble.found_attributes) == 0:
                raise RuntimeError("No attributes found, ensure discover_primary_services() was called.")
            self.fill_handlers()

    def fill_handlers(self):
        """
        This function fills self.ble and self.handlers with key Myo handlers.
        """
        imu_uuid     = get_full_uuid(HardwareServices.IMUDataCharacteristic)
        command_uuid = get_full_uuid(HardwareServices.CommandCharacteristic)
        emg_uuid_0   = get_full_uuid(HardwareServices.EmgData0Characteristic)
        emg_uuid_1   = get_full_uuid(HardwareServices.EmgData1Characteristic)
        emg_uuid_2   = get_full_uuid(HardwareServices.EmgData2Characteristic)
        emg_uuid_3   = get_full_uuid(HardwareServices.EmgData3Characteristic)
        battery_uuid  = HardwareServices.BatteryLevelCharacteristic

        for attribute in self.ble.found_attributes:
            if attribute['uuid'].endswith(imu_uuid):
                # Assumption:
                #       > Client Characteristic Configuration Descriptor comes right after characteristic attribute.
                self.ble.imu_handler             = attribute['chr_handler']
                self.handlers['imu_descriptor']  = attribute['chr_handler'] + 1

            elif attribute['uuid'].endswith(command_uuid):
                self.handlers['command_characteristic'] = attribute['chr_handler']

            elif attribute['uuid'].endswith(emg_uuid_0):
                self.ble.emg_handler_0               = attribute['chr_handler']
                self.handlers['emg_descriptor_0']    = attribute['chr_handler'] + 1
            elif attribute['uuid'].endswith(emg_uuid_1):
                self.ble.emg_handler_1               = attribute['chr_handler']
                self.handlers['emg_descriptor_1']    = attribute['chr_handler'] + 1
            elif attribute['uuid'].endswith(emg_uuid_2):
                self.ble.emg_handler_2               = attribute['chr_handler']
                self.handlers['emg_descriptor_2']    = attribute['chr_handler'] + 1
            elif attribute['uuid'].endswith(emg_uuid_3):
                self.ble.emg_handler_3               = attribute['chr_handler']
                self.handlers['emg_descriptor_3']    = attribute['chr_handler'] + 1

            elif attribute['uuid'].endswith(battery_uuid):
                self.ble.battery_handler = attribute['chr_handler']

        if 'imu_descriptor' not in self.handlers:
            raise RuntimeError("Unable to find IMU attribute, in device's GATT database.")
        if 'command_characteristic' not in self.handlers:
            raise RuntimeError("Unable to find command attribute, in device's GATT database.")
        if 'emg_descriptor_0' not in self.handlers:
            raise RuntimeError("Unable to find EMG attribute 0, in device's GATT database.")
        if 'emg_descriptor_1' not in self.handlers:
            raise RuntimeError("Unable to find EMG attribute 1, in device's GATT database.")
        if 'emg_descriptor_2' not in self.handlers:
            raise RuntimeError("Unable to find EMG attribute 2, in device's GATT database.")
        if 'emg_descriptor_3' not in self.handlers:
            raise RuntimeError("Unable to find EMG attribute 3, in device's GATT database.")
