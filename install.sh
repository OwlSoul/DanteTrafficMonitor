#!/bin/bash

TARGET_DIR="/usr/local/sbin/dante_trafmon"

echo "Installing Dante Traffic Monitor (dante_trafmon)..."
cp src/dante-trafmon/config/dante_trafmon.conf /etc/
mkdir -p $TARGET_DIR
mkdir -p $TARGET_DIR/src/dante_trafmon
mkdir -p $TARGET_DIR/scripts

cp src/dante_trafmon/dante_trafmon.py $TARGET_DIR/src/dante_trafmon/
cp scripts/dante-trafmon-start $TARGET_DIR/scripts/
cp scripts/dante-trafmon-stop $TARGET_DIR/scripts/

echo "Installation completed!"
