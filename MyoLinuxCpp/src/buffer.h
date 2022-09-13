#pragma once
#ifndef BUFFER_H
#define BUFFER_H

#include <vector>

#include "myolinux.h"

namespace MYOLINUX_NAMESPACE {
    /**
     * Buffer used for packing and unpacking packets
     */
    using Buffer = std::vector<unsigned char>;

    /**
     * Pack payload.
     */
    template<typename T>
    Buffer pack(const T &payload)
    {
        const auto ptr = reinterpret_cast<const char*>(&payload);
        return Buffer { ptr, ptr + sizeof(T) };
    }

    /**
     * Unpack payload.
     */
    template<typename T>
    T unpack(const Buffer &buf)
    {
        const auto ptr = reinterpret_cast<const T*>(buf.data());
        return *ptr;
    }
}

#endif //BUFFER_H
