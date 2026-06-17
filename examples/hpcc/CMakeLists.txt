# =============================================================================
# Third-party dependencies for hpcc-validation and hpcc-config-validation
# =============================================================================
#
# 1. yaml-cpp (v0.9.0) — YAML parser for C++
#    - macOS:   brew install yaml-cpp
#    - Ubuntu:  sudo apt-get install libyaml-cpp-dev
#    - Source:  https://github.com/jbeder/yaml-cpp
#
# 2. fmt (v12.1.0) — Modern C++ formatting library
#    - macOS:   brew install fmt
#    - Ubuntu:  sudo apt-get install libfmt-dev
#    - Source:  https://github.com/fmtlib/fmt
#
# =============================================================================
find_package(yaml-cpp REQUIRED)
find_package(fmt REQUIRED)

build_example(
  NAME hpcc-validation
  SOURCE_FILES
        hpcc-validation.cc
        hpcc-config.cc hpcc-config.h
  LIBRARIES_TO_LINK
    ${libcore}
    ${libnetwork}
    ${libinternet}
    ${libapplications}
    ${libpoint-to-point}
    yaml-cpp::yaml-cpp
    fmt::fmt
)

build_example(
        NAME hpcc-config-validation
        SOURCE_FILES
        hpcc-config-validation.cc
        hpcc-config.cc hpcc-config.h
        LIBRARIES_TO_LINK
        ${libcore}
        yaml-cpp::yaml-cpp
        fmt::fmt
)


build_example(
        NAME third-refactored
        SOURCE_FILES
        third-refactored.cc
        LIBRARIES_TO_LINK
        ${libcore}
        ${libnetwork}
        ${libinternet}
        ${libapplications}
        ${libpoint-to-point}
)

build_example(
        NAME hpcc-haoyu
        SOURCE_FILES
        hpcc-haoyu.cc
        LIBRARIES_TO_LINK
        ${libcore}
        ${libnetwork}
        ${libinternet}
        ${libapplications}
        ${libpoint-to-point}
)