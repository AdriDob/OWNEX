# Android Release APK Build Instructions

## Prerequisites

1. **Android SDK**: Install Android SDK (command line tools or Android Studio)
2. **Java 17**: Ensure Java 17 is available
3. **Keystore**: Generate release keystore using `generate_keystore.sh`

## Setup Android SDK

### Option 1: Android Studio
1. Install Android Studio
2. Install SDK platforms (API 24+)
3. Set `sdk.dir` in `android/local.properties`

### Option 2: Command Line Tools
```bash
# Download Android command line tools
# Extract to ~/Android/sdk
# Install required platforms and build tools
$ ~/Android/sdk/cmdline-tools/latest/bin/sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

# Set in android/local.properties:
sdk.dir=/home/youruser/Android/sdk
```

## Generate Release Keystore

```bash
cd android
./generate_keystore.sh
```

This will:
- Create `ownex-release.jks` in the android directory
- Prompt for keystore and key passwords
- Output environment variables to set

**IMPORTANT**: Store the keystore and passwords securely. Never commit to git.

## Build Release APK

### Set Environment Variables

```bash
export OWNEX_KEYSTORE_PATH=/path/to/android/ownex-release.jks
export OWNEX_KEYSTORE_PASSWORD=your_keystore_password
export OWNEX_KEY_ALIAS=ownex
export OWNEX_KEY_PASSWORD=your_key_password
```

### Build

```bash
cd android
./gradlew assembleRelease
```

The release APK will be at:
`android/app/build/outputs/apk/release/app-release.apk`

## Verify Signature

```bash
# Verify APK is signed
apksigner verify --print-certs android/app/build/outputs/apk/release/app-release.apk

# Check package info
aapt dump badging android/app/build/outputs/apk/release/app-release.apk
```

## Testing

### Install via ADB
```bash
adb install android/app/build/outputs/apk/release/app-release.apk
```

### Update Test
1. Build first release APK
2. Install on device
3. Change versionCode in `android/app/build.gradle`
4. Build second release APK with same keystore
5. Install second APK (should update without uninstall)

## Package Information

- **Package ID**: `ai.rastro.app`
- **Version**: `1.0` (versionCode: 1)
- **Min SDK**: 24 (Android 7.0)
- **Target SDK**: 34 (Android 14)

## Security Notes

- Never commit keystore files to git
- Never hardcode passwords in build.gradle
- Use environment variables for sensitive data
- Store keystore backups in secure location
- Document keystore passwords in secure password manager

## Troubleshooting

### SDK not found
- Check `android/local.properties` points to valid SDK directory
- Ensure SDK contains required platforms and build tools

### Signing errors
- Verify environment variables are set
- Check keystore file exists and is readable
- Verify passwords are correct

### Build failures
- Clean build: `./gradlew clean`
- Check Java version: `java -version` (should be 17)
- Verify Gradle wrapper: `./gradlew --version`