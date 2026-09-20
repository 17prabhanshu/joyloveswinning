#!/bin/bash
set -e
echo "Setting up ARM toolchain for macOS locally..."
TOOLCHAIN_DIR="$PWD/arm-toolchain"
if [ ! -d "$TOOLCHAIN_DIR" ]; then
    echo "Downloading gcc-arm-none-eabi..."
    curl -L "https://developer.arm.com/-/media/Files/downloads/gnu-rm/10.3-2021.10/gcc-arm-none-eabi-10.3-2021.10-mac.tar.bz2" -o toolchain.tar.bz2
    echo "Extracting..."
    mkdir -p "$TOOLCHAIN_DIR"
    tar -xjf toolchain.tar.bz2 -C "$TOOLCHAIN_DIR" --strip-components=1
    rm toolchain.tar.bz2
fi
echo "export PATH=\"$TOOLCHAIN_DIR/bin:\$PATH\"" > .env_toolchain
echo "Toolchain ready."
