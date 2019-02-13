 #!/bin/bash
# This script creates deb package for dante_trafmon

PACKAGE_NAME="dante-trafmon"
TARGET_DIR="/usr/local/sbin/dante_trafmon"
BINARY_DIR="/usr/sbin"
LOG_DIR="/var/log/dante_trafmon"

VERSION="1.0.0"

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
Version: $VERSION
Section: base
Priority: optional
Architecture: all
Maintainer: Yury D. (SoulGateW@gmail.com)
Description: Dante Proxy Server traffic monitor.
EOL

# Post-install script
cat > $PACKAGE_NAME/DEBIAN/postinst <<EOL
#!/bin/bash
useradd dante_trafmon -s /bin/false
mkdir $LOG_DIR
chown dante_trafmon:dante_trafmon $LOG_DIR
chown dante_trafmon:dante_trafmon $TARGET_DIR
ln -s $TARGET_DIR/scripts/dante-trafmon-start /usr/sbin/dante-trafmon-start
ln -s $TARGET_DIR/scripts/dante-trafmon-stop /usr/sbin/dante-trafmon-stop
chown dante_trafmon:dante_trafmon /usr/sbin/dante-trafmon-start
chown dante_trafmon:dante_trafmon /usr/sbin/dante-trafmon-stop
EOL

# Post-remove script
cat > $PACKAGE_NAME/DEBIAN/postrm <<EOL
#!/bin/bash
rm $BINARY_DIR/dante-trafmon-start
rm $BINARY_DIR/dante-trafmon-stop
userdel dante_trafmon
rm -rf $LOG_DIR
EOL

chmod 755 $PACKAGE_NAME/DEBIAN/postinst
chmod 755 $PACKAGE_NAME/DEBIAN/postrm

dpkg-deb --build $PACKAGE_NAME

echo "Cleaning..."
rm -rf $PACKAGE_NAME

echo "Done!"
