from core import MyoDongle, joint_event_handler


if __name__ == '__main__':
    device = MyoDongle('/dev/ttyACM0')
    device.clear_state()

    myo_devices = device.discover_myo_devices()
    if len(myo_devices) > 0:
        device.connect(myo_devices[0])
    else:
        print('No devices found, exiting...')
        exit()

    device.enable_imu_readings()
    device.enable_emg_readings()
    device.add_joint_emg_imu_handler(joint_event_handler)

    device.scan_for_data_packets(3)
