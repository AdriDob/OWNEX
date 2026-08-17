#!/bin/bash
# Generate release keystore for OWNEX Android app
# This script creates a keystore for signing release APKs
# Store the keystore securely and never commit it to git

set -e

KEYSTORE_NAME="ownex-release.jks"
KEY_ALIAS="ownex"
KEY_VALIDITY=10000  # 10000 days = ~27 years

echo "Generating OWNEX release keystore..."
echo "This will create: $KEYSTORE_NAME"
echo "Please store the following passwords securely:"
echo ""

# Prompt for passwords
read -sp "Enter keystore password: " KEYSTORE_PASSWORD
echo ""
read -sp "Enter key password: " KEY_PASSWORD
echo ""

# Validate passwords
if [ -z "$KEYSTORE_PASSWORD" ] || [ -z "$KEY_PASSWORD" ]; then
    echo "Error: Passwords cannot be empty"
    exit 1
fi

# Generate keystore
keytool -genkeypair \
    -v \
    -storetype PKCS12 \
    -keystore "$KEYSTORE_NAME" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity $KEY_VALIDITY \
    -storepass "$KEYSTORE_PASSWORD" \
    -keypass "$KEY_PASSWORD" \
    -dname "CN=OWNEX, OU=CATEYE, O=CATEYE, L=Unknown, ST=Unknown, C=AR" \
    2>&1 | tee keystore_generation.log

echo ""
echo "✅ Keystore generated successfully: $KEYSTORE_NAME"
echo ""
echo "IMPORTANT: Store these credentials securely"
echo "Keystore path: $(pwd)/$KEYSTORE_NAME"
echo "Key alias: $KEY_ALIAS"
echo ""
echo "To use this keystore for builds, set these environment variables:"
echo "export OWNEX_KEYSTORE_PATH=$(pwd)/$KEYSTORE_NAME"
echo "export OWNEX_KEYSTORE_PASSWORD=<your_keystore_password>"
echo "export OWNEX_KEY_ALIAS=$KEY_ALIAS"
echo "export OWNEX_KEY_PASSWORD=<your_key_password>"
echo ""
echo "⚠️  NEVER commit the keystore or passwords to git!"