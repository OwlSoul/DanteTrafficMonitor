 #!/bin/bash

PACKAGE_NAME="dante-trafmon"
TARGET_DIR="/usr/local/sbin/dante-trafmon"

VERSION="0.0.2"

echo "Packaging..."
rm -rf $PACKAGE_NAME
mkdir -p $PACKAGE_NAME
mkdir -p $PACKAGE_NAME/DEBIAN
mkdir -p $PACKAGE_NAME/etc
mkdir -p $PACKAGE_NAME$TARGET_DIR/src/dante-trafmon
mkdir -p $PACKAGE_NAME$TARGET_DIR/scripts

cp -rf src/dante-trafmon/config/dante-trafmon.conf $PACKAGE_NAME/etc
cp -rf src/dante-trafmon/dante-trafmon.py $PACKAGE_NAME$TARGET_DIR/src/dante-trafmon
cp -rf scripts/dante-trafmon-start $PACKAGE_NAME$TARGET_DIR/scripts
cp -rf scripts/dante-trafmon-stop $PACKAGE_NAME$TARGET_DIR/scripts

cat > $PACKAGE_NAME/DEBIAN/control <<EOL
Package: dante-trafmon
Version: 0.0.1
Section: base
Priority: optional
Architecture: all
Maintainer: Yury D. (SoulGateW@gmail.com)
Description: Dante Proxy Server traffic monitor.
EOL

dpkg-deb --build $PACKAGE_NAME

echo "Cleaning..."
rm -rf $PACKAGE_NAME

echo "Done!"
