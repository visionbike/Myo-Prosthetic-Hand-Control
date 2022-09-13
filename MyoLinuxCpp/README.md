# MyoLinux

[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

C++ library for interfacing with the Myo armband on Linux (Cloned from [brokenpylons/MyoLinux](https://github.com/brokenpylons/MyoLinux/))

## Features

* Full BLED112 protocol implementation (based on [jrowberg/bglib](https://github.com/jrowberg/bglib))
* GAP/GATT wrapper
    * discovering devices
    * discovering characteristics
    * reading/writing attributes
    * listening to notifications
* myohw protocol (based on [thalmiclabs/myo-bluetooth](https://github.com/thalmiclabs/myo-bluetooth))
    * reading info
    * issuing commands (partial)
    * listening to IMU and EMG events

## Documentation

The documentation can be accessed online [here](https://codedocs.xyz/brokenpylons/MyoLinux/index.html) (clear the browser cache if it doesn't match the source) or generated using Doxygen by running:
```
doxygen
```

## Installation

The binary form of the library can be downloaded [here](https://github.com/brokenpylons/MyoLinux/releases/latest). It is available in deb, rpm and tarball formats for the x86-64 architecture. The library can also be installed the old-fashioned way by compiling it from source. I will cover two installation methods and provide a minimal example to get you started.

### Compiling from source

First thing you will need is the source code, you can download it by clicking [here](https://github.com/brokenpylons/MyoLinux/archive/master.zip) or by cloning the repository:

```
git clone https://github.com/brokenpylons/MyoLinux.git
```

The only nonstandard dependency of this project is CMake 3.20 (at least) which may already be installed by your distribution, if not install it. If you plan to modify the library you might also need Python 3.6 for auto-generating the BLED112 protocol implementation, however this step is otherwise not needed as the generated code is already included in the repository.

For an out-of-source build first create a directory inside the project source tree and switch to it:

```
mkdir build
cd build
```

Call CMake to generate the makefile and call Make to build the library. Finally, install the library to the system (this will probably require the root permissions):

```
cmake ..
make
sudo make install
```

### CMake external project

Include this into your CMakeLists.txt and add the imported target as a dependency.

```
include(ExternalProject)
ExternalProject_Add(MyoLinux
    GIT_REPOSITORY    https://github.com/brokenpylons/MyoLinux.git
    CMAKE_ARGS        -DCMAKE_INSTALL_PREFIX=${CMAKE_CURRENT_BINARY_DIR}/myolinux)
set(myolinux_INCLUDE_DIR ${CMAKE_CURRENT_BINARY_DIR}/myolinux/include)
set(myolinux_LIB_DIR ${CMAKE_CURRENT_BINARY_DIR}/myolinux/lib)
add_library(myolinux SHARED IMPORTED)
set_target_properties(myolinux PROPERTIES IMPORTED_LOCATION ${myolinux_LIB_DIR}/libmyolinux.so)
```

### Example

``` cpp
#include "myolinux/myoclient.h"
#include "myolinux/serial.h"
#include <cinttypes>
using namespace myolinux;
int main()
{
    myo::Client client(Serial{"/dev/ttyACM0", 115200});
    // Autoconnect to the first Myo device
    client.connect();
    if (!client.connected()) {
        return 1;
    }
    // Print device address
    print_address(client.address());
    // Read firmware version
    auto version = client.firmwareVersion();
    std::cout << version.major << "."
        << version.minor << "."
        << version.patch << "."
        << version.hardware_rev << std::endl;
    // Vibrate
    client.vibrate(myo::Vibration::Medium);
    // Read name
    auto name = client.deviceName();
    std::cout << name << std::endl;
    // Set sleep mode (otherwise the device auto disconnects after a while)
    client.setSleepMode(myo::SleepMode::NeverSleep);
    // Read EMG and IMU
    client.setMode(myo::EmgMode::SendEmg, myo::ImuMode::SendData, myo::ClassifierMode::Disabled);
    client.onEmg([](myo::EmgSample sample)
    {
        for (std::size_t i = 0; i < 8; i++) {
            std::cout << static_cast<int>(sample[i]);
            if (i != 7) {
                std::cout << ", ";
            }
        }
        std::cout << std::endl;
    });
    client.onImu([](myo::OrientationSample ori, myo::AccelerometerSample acc, myo::GyroscopeSample gyr)
    {
        std::cout << ori[0] << ", " << ori[1] << ", " << ori[2] << ", " <<  ori[3] << std::endl;
        std::cout << acc[0] << ", " << acc[1] << ", " << acc[2] << std::endl;
        std::cout << gyr[0] << ", " << gyr[1] << ", " << gyr[2] << std::endl;
    });
    for (int i = 0; i < 100; i++) {
        client.listen();
    }
    client.disconnect();
}
```

## Contributing

Please open an issue if you find bugs or any other deficiencies. Pull requests are also welcome. Note that by contributing to this repository you irrevocably license your work under the MPL 2.0.

## Porting

Despite the name, the library might actually also work on Mac and Windows (using Cygwin) without or with minor modifications. If anyone is interested in testing the library on other platforms please open an issue and report your findings.

## License

This repository is placed under the MPL 2.0. See LICENSE for more details.