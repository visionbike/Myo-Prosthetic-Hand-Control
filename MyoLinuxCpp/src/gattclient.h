#pragma once
#ifndef GATTCLIENT_H
#define GATTCLIENT_H

#include <cinttypes>
#include <iostream>
#include <array>
#include <iomanip>
#include <map>

#include "myolinux.h"
#include "bled112client.h"
#include "buffer.h"

namespace MYOLINUX_NAMESPACE {
    namespace gatt {
        namespace notifications {
            const Buffer enable{ 0x1, 0x0 };
            const Buffer disable{ 0x0, 0x0 };
        }

        /**
         * Address of the device.
         * The address byte sequence  is in network order, so it might be in reverse on your architecture.
         * To find the address of your device use the Client::discover method or use the bluetoothctl tool.
         */
        using Address = std::array<std::uint8_t, 6>;

        /**
         * A dictionary mapping characteristics UUIDs to handles.
         */
        using Characteristics = std::map<Buffer, std::uint16_t>;

        /**
         * Exception thrown when the device disconnects.
         */
        class DisconnectedException : public std::exception { };

        /**
         * Class for communication using the GATT protocol.
         */
        class Client
        {
        public:
            Client(const bled112::Client &);

            void discover(std::function<bool(std::int8_t, Address, Buffer)>);
            Characteristics characteristics();
            void connect(const Address &);
            void connect(const std::string &);
            bool connected();
            Address address();

            void disconnect();
            void disconnectAll();

            void writeAttribute(const std::uint16_t, const Buffer &);
            Buffer readAttribute(const std::uint16_t);
            void listen(const std::function<void(std::uint16_t, Buffer)> &);

        private:
            using Event = std::pair<std::uint16_t, Buffer>;

            void disconnect(const std::uint8_t);

            template <typename T>
            T readResponse();

            bled112::Client client;
            bool connected_ = false;
            Address address_;
            std::uint8_t connection;
            std::vector<Event> event_queue;
        };

    }

    void print_address(const gatt::Address &);
}

#endif //GATTCLIENT_H
