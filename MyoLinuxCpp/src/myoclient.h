#pragma once
#ifndef MYOCLIENT_H
#define MYOCLIENT_H

#include <cinttypes>
#include <memory>
#include <map>

#include "myolinux.h"
#include "gattclient.h"
#include "serial.h"
#include "myoapi.h"

namespace MYOLINUX_NAMESPACE {
    namespace myo {
        using Address = gatt::Address;

        /**
         * \copybrief gatt::DisconnectedException
         *
         * This can happen because of inactivity if the myo::SleepMode is set to Normal (set it to NeverSleep to prevent this)
         * or because the device is sending value events faster than your program is processing them.
         * In the latter case decrease the processing latency or put the myo::Client::listen method in a separate thread.
         */
        using DisconnectedException = gatt::DisconnectedException;

        /**
         * Class for communication with the Myo device.
         * This class depends on a gatt::Client instance for issuing GAP/GATT commands to the device.
         */
        class Client {
        public:
            Client(const Serial &);
            Client(const gatt::Client &);

            void discover(std::function<bool(std::int8_t, Address, Buffer)>);
            void connect(const Address &);
            void connect(const std::string &);
            void connect();
            bool connected();
            Address address();
            void disconnect();

            Info info();
            Version firmwareVersion();

            void vibrate(const Vibration);
            void setMode(const EmgMode, const ImuMode, const ClassifierMode);
            void setSleepMode(const SleepMode);

            std::string deviceName();

            void onEmg(const std::function<void(EmgSample)> &);
            void onImu(const std::function<void(OrientationSample, AccelerometerSample, GyroscopeSample)> &);
            void listen();

        private:
            void enable_notifications();

            gatt::Client client;
            std::function<void(EmgSample)> emg_callback;
            std::function<void(OrientationSample, AccelerometerSample, GyroscopeSample)> imu_callback;
        };
    }
}

#undef PACKED

#endif //MYOCLIENT_H
