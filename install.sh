#!/bin/bash

TARGET_DIR="/usr/local/sbin/dante-trafmon"

echo "Installing Dante Traffic Monitor (dante-trafmon)..."
cp src/dante-trafmon/config/dante-trafmon.conf /etc/
mkdir -p $TARGET_DIR
mkdir -p $TARGET_DIR/src/dante-trafmon
mkdir -p $TARGET_DIR/scripts

cp src/dante-trafmon/dante-trafmon.py $TARGET_DIR/src/dante-trafmon/
cp scripts/dante-trafmon-start $TARGET_DIR/scripts/
cp scripts/dante-trafmon-stop $TARGET_DIR/scripts/

echo "Installation completed!"
