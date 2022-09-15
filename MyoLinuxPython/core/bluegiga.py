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

# The implementation of the Bluegiga API
# Reference:
# https://www.silabs.com/products/wireless/bluetooth/bluetooth-low-energy-modules/bled112-bluetooth-smart-dongle"
# https://github.com/sebastiankmiec/PythonMyoLinux/pymyolinux
# See "Bluetooth Smart Software API Reference Manual for BLE Version 1.7" for details.

import struct
import time
import serial
from core.handlers import *
from utils import *


__all__ = ['BlueGigaProtocol']


class BlueGigaProtocol:

    # configurable
    debug = False

    # by default, the BGAPI protocol assumes that UART flow control (RTS/CTS) is used to ensure reliable data
    # transmission and to prevent lost data because of buffer overflows.
    use_rts_cts         = True
    BLED112_BAUD_RATE   = 115200

    # Myo device specific events
    emg_event           = Event("On receiving an EMG data packet from the Myo device.", is_fire=True)
    imu_event           = Event("On receiving an IMU data packet from the Myo device.", is_fire=True)
    joint_emg_imu_event = Event("On receiving an IMU data packet from the Myo device. Use latest IMU event.", is_fire=True)

    # non-empty events
    ble_evt_connection_disconnected     = Event()
    ble_evt_connection_status           = Event()
    ble_evt_gatt_group_found            = Event()
    ble_evt_gatt_procedure_completed    = Event()
    ble_evt_gatt_find_information_found = Event()
    ble_evt_gap_scan_response           = Event()

    # Empty events
    ble_rsp_connection_disconnect   = Event()
    ble_rsp_gatt_find_information   = Event()
    ble_rsp_gatt_attribute_write    = Event()
    ble_evt_gatt_attribute_value    = Event()
    ble_rsp_gatt_read_by_group_type = Event()
    ble_rsp_gap_end_procedure       = Event()
    ble_rsp_gap_discover            = Event()
    ble_rsp_gap_connect_direct      = Event()
    ble_rsp_gap_set_mode            = Event()

    # States
    read_buffer                 = b''
    expected_packet_length      = 0
    busy_reading                = False
    disconnecting               = False

    def __init__(self, port: str):

        self.port           = serial.Serial(port=port, baudrate=self.BLED112_BAUD_RATE, rtscts=self.use_rts_cts)
        self.is_packet_mode = not self.use_rts_cts

        # filled by user of this object
        self.imu_handler     = None
        self.emg_handler_0   = None
        self.emg_handler_1   = None
        self.emg_handler_2   = None
        self.emg_handler_3   = None
        self.battery_handler = None

        # filled by event handlers
        self.myo_devices      = []
        self.found_services   = []
        self.found_attributes = []
        self.connection       = None
        self.current_imu_read = None
        self.battery_level    = None

        # Event handlers
        self.ble_evt_connection_status           += add_connection
        self.ble_evt_connection_disconnected     += disconnect_device
        self.ble_evt_gatt_group_found            += add_found_service
        self.ble_evt_gatt_procedure_completed    += complete_finding_service
        self.ble_evt_gatt_find_information_found += add_found_attribute
        self.ble_evt_gatt_attribute_value        += receive_attribute_value
        self.ble_evt_gap_scan_response           += add_myo_device

        # empty handlers (solely to increment event fire count)
        empty_handler_events = [
            self.ble_rsp_connection_disconnect,
            self.ble_rsp_gatt_read_by_group_type,
            self.ble_rsp_gatt_find_information,
            self.ble_rsp_gatt_attribute_write,
            self.ble_rsp_gap_end_procedure,
            self.ble_rsp_gap_discover,
            self.ble_rsp_gap_connect_direct,
            self.ble_rsp_gap_set_mode,
        ]

        for empty_event in empty_handler_events:
            empty_event += empty_handler

    def transmit_packet(self, packet: bytes):
        """
        Given a bytes object, write to serial.
        Additionally, if in "packet mode" (from the API Reference Manual):
            "When using the BGAPI protocol without UART flow control over a simple 2-wire (TX and RX) UART interface
            and additional length byte needs to be added to the BGAPI packets, which tells the total length of the BGAPI
            packet excluding the length byte itself. This is used by the BGAPI protocol parser to identify the length of
            incoming commands and data and make sure they are fully received."

        :param packet: A bytes object.
        :return:
        """

        # See comment above
        if self.is_packet_mode:
            packet = bytes([len(packet) & 0xFF]) + packet
        if self.debug:
            print('=>[ ' + ' '.join(['%02X' % b for b in packet]) + ' ]')

        self.port.write(packet)

    def read_packets(self, timeout: int = 1):
        """
        Attempt to read bytes from communication port, with no intent of stopping early.

        :param timeout: Time spent reading
        :return: None
        """
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            self.busy_reading = True
            time_spent        = time.time() - start_time
            time_left         = int(timeout - time_spent)

            if time_left > 0:
                self.read_bytes(time_left)

    def read_packets_conditional(self, evt: EventType, timeout: int = 2):
        """
        Attempt to read bytes from communication port, prematurely stopping on occurence of an event.

        :param evt: An event of interest (all events are defined at the start of BlueGigaProtocol)
        :param timeout: Time spent reading
        :return: Boolean, True => the event occurred
        """

        # Check if event has already occured
        if self.get_event_count(evt) > 0:
            self.__eventcounter__[evt] = 0
            return True

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            self.busy_reading   = True
            time_spent          = time.time() - start_time
            time_left           = int(timeout - time_spent)

            if time_left > 0:
                self.read_bytes(time_left)

            if self.get_event_count(evt) > 0:
                self.__eventcounter__[evt] = 0
                return True
        return False

    def get_event_count(self, evt: EventType):
        """
        Returns the current event count of event, incremented by event handlers.

        :param evt: An event of interest (all events are defined at the start of BlueGigaProtocol)
        :return: A count
        """

        if hasattr(self, '__eventcounter__'):
            if evt in self.__eventcounter__:
                return self.__eventcounter__[evt]
        return 0

    def read_bytes(self, timeout: int):
        """
        Attempts to read bytes from the communication port, and calls parse_byte() for processing.

        :param timeout: Time spent reading
        :return: Boolean, True => a byte was read, and it is not the last byte of a packet
        """
        self.port.timeout = timeout

        while True:
            byte_read = self.port.read(size=1)
            if len(byte_read) > 0:
                self.parse_byte(byte_read[0])
            else:
                # timeout
                self.busy_reading = False
            if not self.busy_reading:
                # either
                # 1. no bytes read
                # 2. last byte of packet read
                break

        return self.busy_reading

    def parse_byte(self, byte_read: int):
        """
        Keeps track of bytes read. Upon completion of reading bytes from a packet, trigger an appropirate event.

        BGAPI packet format (from the API reference manual), as of 12/18/2018:

            --------------------------------------------------------------------------------
            |Octet | Octet | Length | Description           | Notes                        |
            |      | bits  |        |                       |                              |
            -------------------------------------------------------------------------------|
            | 0    | 7     | 1 bit  | Message Type (MT)     | 0: Command/Response          |
            |      |       |        |                       | 1: Event                     |
            |      |       |        |                       |                              |
            -------------------------------------------------------------------------------|
            | ...  | 6:3   | 4 bits | Technology Type (TT)  | 0000: Bluetooth Smart        |
            |      |       |        |                       | 0001: Wi-Fi                  |
            |      |       |        |                       |                              |
            --------------------------------------------------------------------------------
            | ...  | 2:0   | 3 bits | Length High (LH)      | Payload length (high bits)   |
            --------------------------------------------------------------------------------
            | 1    | 7:0   | 8 bits | Length Low (LL)       | Payload length (low bits)    |
            --------------------------------------------------------------------------------
            | 2    | 7:0   | 8 bits | Class ID (CID)        | Command class ID             |
            --------------------------------------------------------------------------------
            | 3    | 7:0   | 8 bits | Command ID (CMD)      | Command ID                   |
            --------------------------------------------------------------------------------
            | 4-n  | -     | 0-2048 | Payload (PL)          | Up to 2048 bytes of payload  |
            |      |       | Bytes  |                       |                              |
            --------------------------------------------------------------------------------

        :param byte_read: A byte read via read_bytes().
        :return: None
        """

        if (len(self.read_buffer) == 0) and (byte_read in [BluetoothMessages.bluetooth_resp,
                                                           BluetoothMessages.bluetooth_event,
                                                           WifiMessages.wifi_resp,
                                                           WifiMessages.wifi_event]):
            # if valid Message/Technology Types
            self.read_buffer += bytes([byte_read])
        elif len(self.read_buffer) == 1:
            self.read_buffer           += bytes([byte_read])
            self.expected_packet_length = PackageMessages.packet_header_length + (self.read_buffer[0] & PackageMessages.packet_length_high_bits) + self.read_buffer[1]  # Payload length (low bits)
        elif len(self.read_buffer) > 1:
            self.read_buffer += bytes([byte_read])

        if (self.expected_packet_length > 0) and (len(self.read_buffer) == self.expected_packet_length):
            # read last byte of a packet, fire appropriate events
            if self.debug:
                print('<=[ ' + ' '.join(['%02X' % b for b in self.read_buffer]) + ' ]')

            packet_type, _, class_id, command_id = self.read_buffer[:PackageMessages.packet_header_length]
            packet_payload = self.read_buffer[PackageMessages.packet_header_length:]

            # note: Part of this byte (and next byte "_") contains bits for payload length
            packet_type = packet_type & PackageMessages.packet_type_bits

            # reset for next packet
            self.read_buffer = bytes([])

            if packet_type == BluetoothMessages.bluetooth_resp:
                # (1) Bluetooth response packets
                if class_id == BGAPIClasses.Connection:
                    # Connection packets
                    if command_id == ConnectionResponseCommands.ble_rsp_connection_disconnect:
                        connection, result = struct.unpack('<BH', packet_payload[:3])
                        if result != BleResponseConditions.disconnect_procedure_started:
                            if self.debug:
                                print(f"Failed to start disconnect procedure for connection {connection}.")
                        else:
                            self.disconnecting = True
                            if self.debug:
                                print(f"Started disconnect procedure for connection {connection}.")
                        self.ble_rsp_connection_disconnect(**dict(connection=connection, result=result))
                elif class_id == BGAPIClasses.GATT:
                    # GATT packets - discover services, acquire data
                    if command_id == GATTResponseCommands.ble_rsp_gatt_read_by_group_type:
                        connection, result = struct.unpack('<BH', packet_payload[:3])
                        self.ble_rsp_gatt_read_by_group_type(**dict(connection=connection, result=result))
                    elif command_id == GATTResponseCommands.ble_rsp_gatt_find_information:
                        connection, result = struct.unpack('<BH', packet_payload[:3])
                        if result != BleResponseConditions.find_info_success:
                            if self.debug:
                                print("Error using find information command.")
                        self.ble_rsp_gatt_find_information(**dict(connection=connection, result=result))
                    elif command_id == GATTResponseCommands.ble_rsp_gatt_attribute_write:
                        connection, result = struct.unpack('<BH', packet_payload[:3])
                        if result != BleResponseConditions.write_success:
                            raise "Write attempt was unsuccessful."
                        self.ble_rsp_gatt_attribute_write(**dict(connection=connection, result=result))
                elif class_id == BGAPIClasses.GAP:
                    # GAP packets - advertise, observe, connect
                    if command_id == GAPResponseCommands.ble_rsp_gap_set_mode:
                        result = struct.unpack('<H', packet_payload[:2])[0]
                        if result != BleResponseConditions.gap_set_mode_success:
                            raise RuntimeError("Failed to set GAP mode.")
                        else:
                            if self.debug:
                                print("Successfully set GAP mode.")
                        self.ble_rsp_gap_set_mode(**dict(result=result))
                    elif command_id == GAPResponseCommands.ble_rsp_gap_discover:
                        result = struct.unpack('<H', packet_payload[:2])[0]
                        if result != BleResponseConditions.gap_start_procedure_success:
                            raise RuntimeError("Failed to start GAP discover procedure.")
                        self.ble_rsp_gap_discover(**dict(result=result))
                    elif command_id == GAPResponseCommands.ble_rsp_gap_connect_direct:
                        result, connection_handle = struct.unpack('<HB', packet_payload[:3])
                        if result != BleResponseConditions.gap_start_procedure_success:
                            raise RuntimeError("Failed to start GAP connection procedure.")
                        self.ble_rsp_gap_connect_direct(**dict(result=result, connection_handle=connection_handle))
                    elif command_id == GAPResponseCommands.ble_rsp_gap_end_procedure:
                        result = struct.unpack('<H', packet_payload[:2])[0]
                        if result != BleResponseConditions.gap_end_procedure_success:
                            if self.debug:
                                print("Failed to end GAP procedure.")
                        self.ble_rsp_gap_end_procedure(**dict(result=result))
            elif packet_type == BluetoothMessages.bluetooth_event:
                # (2) Bluetooth event packets
                if class_id == BGAPIClasses.Connection:
                    # connection packets
                    if command_id == ConnectionEventCommands.ble_evt_connection_status:
                        connection, flags, address, address_type, conn_interval, timeout, latency, bonding = struct.unpack('<BB6sBHHHB', packet_payload[:16])
                        args = dict(connection=connection, flags=flags, address=address, address_type=address_type, conn_interval=conn_interval, timeout=timeout, latency=latency, bonding=bonding)
                        print(f"Connected to a device with the following parameters:\n{args}")
                        self.ble_evt_connection_status(**args)
                    elif command_id == ConnectionEventCommands.ble_evt_connection_disconnected:
                        connection, reason = struct.unpack('<BH', packet_payload[:3])
                        if (self.connection is None) or (connection == self.connection['connection']):
                            self.ble_evt_connection_disconnected(**dict(connection=connection, reason=reason))
                elif class_id == BGAPIClasses.GATT:
                    # GATT packets - discover services, acquire data
                    if command_id == GATTEventCommands.ble_evt_gatt_procedure_completed:
                        connection, result, chr_handler = struct.unpack('<BHH', packet_payload[:5])
                        if (self.connection is not None) and (connection == self.connection['connection']):
                            self.ble_evt_gatt_procedure_completed(**dict(connection=connection, result=result, chr_handler=chr_handler))
                    elif command_id == GATTEventCommands.ble_evt_gatt_group_found:
                        connection, start, end, uuid_len = struct.unpack('<BHHB', packet_payload[:6])
                        if (self.connection is not None) and (connection == self.connection['connection']):
                            uuid_data = packet_payload[6:]
                            self.ble_evt_gatt_group_found(**dict(connection=connection, start=start, end=end, uuid=uuid_data))
                    elif command_id == GATTEventCommands.ble_evt_gatt_find_information_found:
                        connection, chr_handler, uuid_len = struct.unpack('<BHB', packet_payload[:4])
                        uuid_data = packet_payload[4:]
                        if (self.connection is not None) and (connection == self.connection['connection']):
                            self.ble_evt_gatt_find_information_found(**dict(connection=connection, chr_handler=chr_handler, uuid=uuid_data))
                    elif command_id == GATTEventCommands.ble_evt_gatt_attribute_value:
                        connection, att_handler, att_type, value_len = struct.unpack('<BHBB', packet_payload[:5])
                        if (self.connection is not None) and (connection == self.connection['connection']):
                            value_data = packet_payload[5:]
                            self.ble_evt_gatt_attribute_value(**dict(connection=connection, att_handler=att_handler, att_type=att_type, att_value=value_data))
                elif class_id == BGAPIClasses.GAP:
                    # GAP packets - advertise, observe, connect
                    if command_id == GAPEventCommands.ble_evt_gap_scan_response:
                        rssi, packet_type, address, address_type, bond, data_len = struct.unpack('<bB6sBBB', packet_payload[:11])
                        data = packet_payload[11:]
                        self.ble_evt_gap_scan_response(**dict(rssi=rssi, packet_type=packet_type, address=address, address_type=address_type, bond=bond, data=data))
                    elif command_id == GAPEventCommands.ble_evt_gap_mode_changed:
                        # discover, connect = struct.unpack('<BB', packet_payload[:2])
                        # self.ble_evt_gap_mode_changed({ 'discover': discover, 'connect': connect })
                        pass
            elif packet_type == WifiMessages.wifi_resp:
                # (3) Wifi response packet
                pass
            else:
                # (4) Wifi event packet
                pass
            # reset
            self.busy_reading = False

    def ble_cmd_connection_disconnect(self, connection: bytes):
        """
        # Byte Array Packing Functions ---> Construct all necessary BGAPI messages
        This command disconnects an active Bluetooth connection.
        -> When link is disconnected a Disconnected event is produced.

        :param connection: Connection handle to close
        :return: Bytes object
        """

        payload_length  = 1
        packet_class    = BGAPIClasses.Connection
        message_id      = GATTTransmitCommands.ble_tmt_connection_disconnect
        return struct.pack('<4BB', CommandMessages.command_message, payload_length, packet_class, message_id, connection)

    def ble_cmd_attclient_read_by_group_type(self, connection: int, start: bytes, end: bytes, uuid: bytes):
        """
        This command reads the value of each attribute of a given type and in a given handle range.
        -> The command is typically used for primary (UUID: 0x2800) and secondary (UUID: 0x2801) service discovery.
        -> Discovered services are reported by Group Found event.
        -> Finally when the procedure is completed a Procedure Completed event is generated.

        :param connection: Connection Handle
        :param start: First requested handle number
        :param end: Last requested handle number
        :param uuid: Group UUID to find
        :return: Bytes object
        """

        payload_length  = 6 + len(uuid)
        packet_class    = BGAPIClasses.GATT
        message_id      = GATTTransmitCommands.ble_tmt_attclient_read_by_group_type
        return struct.pack('<4BBHHB' + str(len(uuid)) + 's', CommandMessages.command_message, payload_length, packet_class, message_id, connection, start, end, len(uuid), bytes(i for i in uuid))

    def ble_cmd_attclient_find_information(self, connection: int, start: bytes, end: bytes):
        """
        This command is used to discover attribute handlers and their types (UUIDs) in a given handle range.
        -> Causes attclient find_information_found and attclient procedure_completed

        :param connection: Connection handle
        :param start: First attribute handle
        :param end: Last attribute handle
        :return: Bytes object
        """
        payload_length  = 5
        packet_class    = BGAPIClasses.GATT
        messaged_id     = GATTTransmitCommands.ble_tmt_attclient_find_information
        return struct.pack('<4BBHH', CommandMessages.command_message, payload_length, packet_class, messaged_id, connection, start, end)

    def ble_cmd_attclient_attribute_write(self, connection: int, att_handler: bytes, data: bytes):
        """
        This command can be used to write an attributes value on a remote device. In order to write the value of an attribute a Bluetooth connection must exist.
        -> A successful attribute write will be acknowledged by the remote device and this will generate an event attclient_procedure_completed.

        :param connection: Connection handle
        :param att_handler: Attribute handle to write to
        :param data: Attribute value
        :return: Bytes object
        """

        payload_length  = 4 + len(data)
        packet_class    = BGAPIClasses.GATT
        message_id      = GATTTransmitCommands.ble_tmt_attclient_attribute_write
        return struct.pack('<4BBHB' + str(len(data)) + 's', CommandMessages.command_message, payload_length, packet_class, message_id, connection, att_handler, len(data), bytes(i for i in data))

    def ble_cmd_gap_set_mode(self, discover: int, connect: int):
        """
        This command configures the current GAP discoverability and connectability modes.
        It can be used to enable advertisements and/or allow connection.
        The command is also meant to fully stop advertising.

        :param discover: GAP Discoverable Mode
        :param connect: GAP Connectable Mode
        :return: Bytes object
        """

        payload_length  = 2
        packet_class    = BGAPIClasses.GAP
        message_id      = GAPTransmitCommands.ble_tmt_gap_set_mode
        return struct.pack('<4BBB', CommandMessages.command_message, payload_length, packet_class, message_id, discover, connect)

    def ble_cmd_gap_discover(self, mode: bytes):
        """
        This command starts the GAP discovery procedure to scan for advertising devices i.e. to perform a device discovery.
        -> Scanning parameters can be configured with the Set Scan Parameters command before issuing this command.
        -> To cancel on an ongoing discovery process use the End Procedure command.

        :param mode: GAP Discover mode
        :return: Bytes object
        """

        payload_length  = 1
        packet_class    = BGAPIClasses.GAP
        message_id      = GAPTransmitCommands.ble_tmt_gap_discover
        return struct.pack('<4BB', CommandMessages.command_message, payload_length, packet_class, message_id, mode)

    def ble_cmd_gap_connect_direct(self, address: bytes, addr_type: int, conn_interval_min: int, conn_interval_max: int, timeout: int, latency: int):
        """
        This command will start the GAP direct connection establishment procedure to a dedicated Bluetooth Smart device.
        1) The Bluetooth module will enter a state where it continuously scans for the connectable
        advertisement packets from the remote device which matches the Bluetooth address gives as a parameter.
        2) Upon receiving the advertisement packet, the module will send a connection request packet to the
        target device to initiate a Bluetooth connection. A successful connection will be indicated by a status event.
        -> The connection establishment procedure can be cancelled with End Procedure command.

        :param address: Bluetooth address of the target device
        :param addr_type: Bluetooth address type
        :param conn_interval_min: Minimum Connection Interval (in units of 1.25ms). (Range: 6 - 3200)
        :param conn_interval_max: Minimum Connection Interval (in units of 1.25ms). (Range: 6 - 3200)
        :param timeout: Supervision Timeout (in units of 10ms). The Supervision Timeout defines how long the devices
                        can be out of range before the connection is closed. (Range: 10 - 3200)
        :param latency: This parameter configures the slave latency. Slave latency defines how many connection
                        intervals a slave device can skip. Increasing slave latency will decrease the energy
                        consumption of the slave in scenarios where slave does not have data to send at every
                        connection interval. (Range: 0 - 500)
        :return: Bytes object
        """

        payload_length  = 15
        packet_class    = BGAPIClasses.GAP
        message_id      = GAPTransmitCommands.ble_tmt_gap_connect_direct
        return struct.pack('<4B6sBHHHH', CommandMessages.command_message, payload_length, packet_class, message_id, bytes(i for i in address), addr_type, conn_interval_min, conn_interval_max, timeout, latency)

    def ble_cmd_gap_end_procedure(self):
        """
        This command ends the current GAP discovery procedure and stop the scanning of advertising devices.

        :return: Bytes object
        """

        payload_length  = 0
        packet_class    = BGAPIClasses.GAP
        message_id      = GAPTransmitCommands.ble_tmt_gap_end_procedure
        return struct.pack('<4B', CommandMessages.command_message, payload_length, packet_class, message_id)

    def ble_cmd_attclient_read_by_handle(self, connection: int, chr_handler: bytes):
        """
        This command reads a remote attribute's value with the given handle. Read by handle can be used to read
        attributes up to 22 bytes long. For longer attributes Read Long command must be used.

        :param connection: Connection handle
        :param chr_handler: Attribute handle
        :return: Bytes object
        """

        payload_length  = 3
        packet_class    = BGAPIClasses.GATT
        message_id      = GATTTransmitCommands.ble_tmt_attclient_read_by_handle
        return struct.pack('<4BBH', CommandMessages.command_message, payload_length, packet_class, message_id, connection, chr_handler)
