#!/bin/bash

# Trmex AI Assistant - APK Build Script
# This script automates the APK building process

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Main script
print_header "Trmex AI Assistant - APK Builder"

# Check prerequisites
print_header "Checking Prerequisites"

if ! command -v flutter &> /dev/null; then
    print_error "Flutter is not installed. Please install Flutter from https://flutter.dev"
    exit 1
fi
print_success "Flutter is installed"

if ! command -v java &> /dev/null; then
    print_error "Java is not installed. Please install JDK 17+"
    exit 1
fi
print_success "Java is installed"

# Navigate to frontend directory
if [ -d "frontend" ]; then
    cd frontend
    print_success "Navigated to frontend directory"
else
    print_error "frontend directory not found. Please run this script from the project root."
    exit 1
fi

# Flutter doctor check
print_header "Running Flutter Doctor"
flutter doctor --android-licenses

# Get dependencies
print_header "Installing Dependencies"
flutter pub get
print_success "Dependencies installed"

# Clean previous builds
print_header "Cleaning Previous Builds"
flutter clean
cd android
./gradlew clean
cd ..
print_success "Build cache cleaned"

# Ask for build type
print_header "Select Build Type"
echo "1) Debug APK (faster, for testing)"
echo "2) Release APK (optimized, for distribution)"
echo "3) Split APKs (smaller files for different architectures)"
read -p "Enter your choice (1-3): " BUILD_CHOICE

case $BUILD_CHOICE in
    1)
        print_header "Building Debug APK"
        flutter build apk --debug
        APK_PATH="build/app/outputs/flutter-apk/app-debug.apk"
        ;;
    2)
        print_header "Building Release APK"
        flutter build apk --release --android-skip-build-dependency-validation
        APK_PATH="build/app/outputs/flutter-apk/app-release.apk"
        ;;
    3)
        print_header "Building Split APKs"
        flutter build apk --split-per-abi --release
        APK_PATH="build/app/outputs/flutter-apk/"
        ;;
    *)
        print_error "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Verify build
if [ "$BUILD_CHOICE" == "3" ]; then
    if [ -f "build/app/outputs/flutter-apk/app-arm64-v8a-release.apk" ]; then
        print_success "APK Build Completed Successfully!"
        print_header "Build Output"
        echo -e "${GREEN}Split APKs created:${NC}"
        ls -lh build/app/outputs/flutter-apk/app-*-release.apk
    else
        print_error "APK build failed"
        exit 1
    fi
else
    if [ -f "$APK_PATH" ]; then
        print_success "APK Build Completed Successfully!"
        print_header "Build Output"
        echo -e "${GREEN}APK Location:${NC}"
        ls -lh "$APK_PATH"
        
        # Calculate APK size
        SIZE=$(du -h "$APK_PATH" | cut -f1)
        echo -e "${GREEN}APK Size: $SIZE${NC}"
    else
        print_error "APK build failed"
        exit 1
    fi
fi

# Optional: Install on connected device
print_header "Installation"
read -p "Do you want to install the APK on a connected device? (y/n): " INSTALL_CHOICE

if [ "$INSTALL_CHOICE" == "y" ] || [ "$INSTALL_CHOICE" == "Y" ]; then
    if [ -f "$APK_PATH" ]; then
        print_header "Installing APK"
        adb install -r "$APK_PATH"
        print_success "APK installed successfully"
    else
        print_error "APK file not found for installation"
    fi
fi

print_header "Build Complete"
echo -e "${GREEN}Trmex AI Assistant APK is ready for deployment!${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "1. Update the API endpoint in lib/main.dart (line 41)"
echo "2. Test on an emulator or device before production release"
echo "3. For Play Store, build an app bundle (AAB) instead"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "• Review APK_BUILD_GUIDE.md for detailed information"
echo "• Test the app thoroughly on different devices"
echo "• Configure backend connection before production"
