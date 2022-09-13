#pragma once
#ifndef SERIAL_H
#define SERIAL_H

#include <string>
#include <vector>

#include "myolinux.h"
#include "buffer.h"

namespace  MYOLINUX_NAMESPACE {
    class Serial
    {
    public:
        Serial(const std::string &, const int);
        Buffer read(const std::size_t);
        std::size_t write(const Buffer &);
    private:
        int fd;
    };
}

#endif //SERIAL_H
