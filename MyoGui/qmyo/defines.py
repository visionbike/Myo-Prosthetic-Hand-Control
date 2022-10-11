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

from typing import NamedTuple
from enum import IntEnum

__all__ = [
    'NotifHandle', 'CommandHandle', 'InfoHandle',
    'SKU', 'HardwareRevision',
    'Arm', 'Pose', 'XDirection',
    'EmgMode', 'ImuMode', 'ClassifierMode', 'SleepMode',
    'UnlockMode', 'UserActionMode', 'VibrationMode',
    'ClassificationModel', 'ClassificationEvent', 'MotionEvent',
    'BasicInfo', 'FirmwareVersion',
]


class InfoHandle(IntEnum):
    BATTERY  = 0x10
    INFO     = 0x14
    FIRMWARE = 0x16
    COMMAND  = 0x18


class NotifHandle(IntEnum):
    IMU        = 0x1b
    MOTION     = 0x1e
    CLASSIFIER = 0x22
    EMG_PROC   = 0x26
    EMG_0      = 0x2a
    EMG_1      = 0x2d
    EMG_2      = 0x30
    EMG_3      = 0x33
    # handle_emgs = ['d5060105-a904-deb9-4748-2c7f4a124842', 'd5060205-a904-deb9-4748-2c7f4a124842', 'd5060305-a904-deb9-4748-2c7f4a124842', 'd5060405-a904-deb9-4748-2c7f4a124842']


class CommandHandle(IntEnum):
    SET_MODE       = 0x01
    VIBRATE        = 0x03
    DEEP_SLEEP     = 0x04
    SET_LED        = 0x06
    VIBRATE2       = 0x07
    SET_SLEEP_MODE = 0x09
    UNLOCK         = 0xa
    USER_ACTION    = 0xb


class SKU(IntEnum):
    UNKNOWN = 0     # default value for old firmwares
    BLACK   = 1     # black Myo SKU
    WHITE   = 2     # white Myo SKU


class HardwareRevision(IntEnum):
    UNKNOWN = 0     # unknown hardware revision
    REV_C   = 1     # Myo Alpha (REV-C) hardware
    REV_D   = 2     # Myo (REV_D) hardware


class Arm(IntEnum):
    RIGHT   = 0x01
    LEFT    = 0X02
    UNKNOWN = 0xff


class XDirection(IntEnum):
    WRIST   = 0x01
    ELBOW   = 0x02
    UNKNOWN = 0xff


class Pose(IntEnum):
    REST           = 0x00
    FIRST          = 0x01
    WAVE_IN        = 0x02
    WAVE_OUT       = 0x03
    FINGER_TAP     = 0x04
    THUMB_TO_PINKY = 0x05
    UNKNOWN        = 0xff


class EmgMode(IntEnum):
    NONE = 0x00  # do not send EMG data
    PROC = 0x01  # SEND 50Hz rectified and band-pass filtered data
    FILT = 0x02  # send 200Hz filtered EMG Data but not rectified data
    RAW  = 0x03  # send 200Hz raw EMG Data from ADC ranged between -128 to 127


class ImuMode(IntEnum):
    NONE  = 0x00    # do not send IMU data
    DATA  = 0x01    # send IMU data streams (accelerometers, gyroscope, and orientation)
    EVENT = 0x02    # send motion events detected by IMU (e.g., taps)
    ALL   = 0x03    # send both IMU data streams and motion events
    RAW   = 0x04    # send raw IMU data streams


class ClassifierMode(IntEnum):
    DISABLED = 0x00     # disable and reset internal state of the onboard classifier
    ENABLED  = 0x01     # send classifier events (poses and arm events


class SleepMode(IntEnum):
    NORMAL      = 0x00  # normal sleep mode; Myo will sleep after a period of inactivity
    NEVER_SLEEP = 0x01  # never go to sleep


class UnlockMode(IntEnum):
    LOCK  = 0x00  # re-lock immediately
    TIMED = 0x01  # unlock now and re-lock after a fixed timeout
    HOLD  = 0x02  # unlock now and remain unlocked until a lock command is received


class UserActionMode(IntEnum):
    SINGLE = 0X00  # user did a single, discrete action, such as pausing a video


class VibrationMode(IntEnum):
    NONE   = 0x00   # do not vibrate
    SHORT  = 0x01   # vibrate with a short amount of time
    MEDIUM = 0x02   # vibrate with a medium amount of time
    LONG   = 0x03   # vibrate with a long amount of time


class ClassificationModel(IntEnum):
    BUILT  = 0x00   # model built into Myo
    CUSTOM = 0x01   # model based on personalized user data


class ClassificationEvent(IntEnum):
    ARM_SYNCED   = 0x01
    ARM_UNSYNCED = 0x02
    POSE         = 0x03
    UNLOCKED     = 0x04
    LOCKED       = 0x05
    SYNC_FAILED  = 0x06


class MotionEvent(IntEnum):
    TAP = 0x00


class BasicInfo(NamedTuple):
    """
    Basic information of Myo device
    """

    serial_number: bytearray
    unlock_pose: Pose
    classifier_type: ClassifierMode
    classifier_index: int
    has_custom_classifier: bool
    stream_indicating: bool
    sku: SKU


class FirmwareVersion(NamedTuple):
    major: int                      # major version is incremented for changes in this interface
    minor: int                      # minor version is incremented for changes in this interface
    patch: int                      # patch version is incremented for firmware changes that do not introduce changes in this interfaces
    hardware_rev: HardwareRevision  # Myo hardware revision
