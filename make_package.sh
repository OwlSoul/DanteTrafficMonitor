 #!/bin/bash

PACKAGE_NAME="dante-trafmon"
TARGET_DIR="/usr/local/sbin/dante_trafmon"
BINARY_DIR="/usr/sbin"

VERSION="0.0.2"

echo "Packaging..."
rm -rf $PACKAGE_NAME
mkdir -p $PACKAGE_NAME
mkdir -p $PACKAGE_NAME/DEBIAN
mkdir -p $PACKAGE_NAME/etc
mkdir -p $PACKAGE_NAME$TARGET_DIR/src/dante_trafmon
mkdir -p $PACKAGE_NAME$TARGET_DIR/scripts

cp -rf src/dante_trafmon/config/dante_trafmon.conf $PACKAGE_NAME/etc
cp -rf src/dante_trafmon/dante_trafmon.py $PACKAGE_NAME$TARGET_DIR/src/dante_trafmon
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

cat > $PACKAGE_NAME/DEBIAN/postinst <<EOL
#!/bin/bash
ln -s $TARGET_DIR/scripts/dante-trafmon-start /usr/sbin/dante-trafmon-start
ln -s $TARGET_DIR/scripts/dante-tradmon-stop /usr/sbin/dante-trafmon-stop
EOL

dpkg-deb --build $PACKAGE_NAME

echo "Cleaning..."
rm -rf $PACKAGE_NAME

echo "Done!"
