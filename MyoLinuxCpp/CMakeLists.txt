cmake_minimum_required(VERSION 3.22)
project(MyoLinuxCpp)

set(CMAKE_CXX_STANDARD 17)

set(HEADERS
    src/buffer.h
    src/serial.h
    src/bleapi.h
    src/bled112client.h
    src/gattclient.h
    src/myoclient.h
    src/myoapi.h
    src/firstargument.h
    src/myolinux.h)

set(PRIVATE_HEADERS
    src/myoapi_p.h)

set(SRC
    src/generator.py
    src/bleapi.xml
    src/serial.cpp
    src/gattclient.cpp
    src/myoclient.cpp
    ${HEADERS}
    ${PRIVATE_HEADERS})

set(EXAMPLE_SRC
    src/main.cpp
    ${HEADERS})

add_library(${PROJECT_NAME} SHARED ${SRC})
set_property(TARGET ${PROJECT_NAME} PROPERTY CXX_STANDARD 17)

add_executable(${PROJECT_NAME}_example ${EXAMPLE_SRC})
set_property(TARGET ${PROJECT_NAME}_example PROPERTY CXX_STANDARD 17)
target_link_libraries(${PROJECT_NAME}_example ${PROJECT_NAME})

set(CPACK_PACKAGE_NAME "myolinuxcpp")
set(CPACK_PACKAGE_VERSION "1.0.0")
set(CPACK_PACKAGE_INSTALL_DIRECTORY /usr)
set(CPACK_PACKAGE_CONTACT "Žiga Leber <brokenpylons@gmail.com>")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "C++ library for interfacing with the Myo armband on Linux.")
execute_process(COMMAND uname -m OUTPUT_VARIABLE CPACK_PACKAGE_ARCHITECTURE OUTPUT_STRIP_TRAILING_WHITESPACE)
set(CPACK_PACKAGE_FILE_NAME "${CMAKE_PROJECT_NAME}_${CPACK_PACKAGE_VERSION}_${CPACK_PACKAGE_ARCHITECTURE}")

set(CPACK_GENERATOR "DEB;RPM;TGZ")

install(TARGETS ${PROJECT_NAME} LIBRARY DESTINATION lib)
install(FILES ${HEADERS} DESTINATION include/myolinux)

include(CPack)