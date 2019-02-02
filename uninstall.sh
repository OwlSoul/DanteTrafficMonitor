#!/bin/sh

TARGET_DIR="/usr/local/sbin/dante-trafmon"

echo "Uninstalling Dante Traffic Monitor..."
rm -f /etc/dante-trafmon.conf
rm -rf $TARGET_DIR
echo "DONE!"
