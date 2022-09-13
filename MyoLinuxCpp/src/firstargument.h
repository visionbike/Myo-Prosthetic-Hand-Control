#pragma once
#ifndef FIRSTARGUMENT_H
#define FIRSTARGUMENT_H

#include <type_traits>

#include "myolinux.h"

namespace MYOLINUX_NAMESPACE {
    template <typename T>
    struct FirstArgument : FirstArgument<decltype(&T::operator())> { };

    template <typename R, typename A, typename... Args>
    struct FirstArgument<R(A, Args...)> {
        using type = A;
    };

    template <typename R, typename A, typename... Args>
    struct FirstArgument<R(*)(A, Args...)> {
        using type = A;
    };

    template <typename T, typename R, typename A, typename... Args>
    struct FirstArgument<R (T::*)(A, Args...)> {
        using type = A;
    };

    template <typename T, typename R, typename A, typename... Args>
    struct FirstArgument<R (T::*)(A, Args...) const> {
        using type = A;
    };

    template <typename T, typename R, typename A, typename... Args>
    struct FirstArgument<R (T::*)(const A&, Args...)> {
        using type = A;
    };

    template <typename T, typename R, typename A, typename... Args>
    struct FirstArgument<R (T::*)(const A&, Args...) const> {
        using type = A;
    };
}

#endif //FIRSTARGUMENT_H
