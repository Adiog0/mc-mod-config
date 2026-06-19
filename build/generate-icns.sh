#!/usr/bin/env bash
# generate-icns.sh — Generate macOS .icns from pickaxe.png
# Run on macOS: ./build/generate-icns.sh
#
# Requires: sips + iconutil (built-in on macOS)
#
# Output: build/icon.icns

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PNG="$SCRIPT_DIR/../icons/pickaxe.png"
ICONSET="$SCRIPT_DIR/icon.iconset"
ICNS="$SCRIPT_DIR/icon.icns"

if [ ! -f "$PNG" ]; then
    echo "ERROR: $PNG not found"
    exit 1
fi

# Create iconset directory
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

# Generate all required sizes
sips -z 16 16   "$PNG" --out "$ICONSET/icon_16x16.png"
sips -z 32 32   "$PNG" --out "$ICONSET/icon_16x16@2x.png"
sips -z 32 32   "$PNG" --out "$ICONSET/icon_32x32.png"
sips -z 64 64   "$PNG" --out "$ICONSET/icon_32x32@2x.png"
sips -z 128 128 "$PNG" --out "$ICONSET/icon_128x128.png"
sips -z 256 256 "$PNG" --out "$ICONSET/icon_128x128@2x.png"
sips -z 256 256 "$PNG" --out "$ICONSET/icon_256x256.png"
sips -z 512 512 "$PNG" --out "$ICONSET/icon_256x256@2x.png"
sips -z 512 512 "$PNG" --out "$ICONSET/icon_512x512.png"
sips -z 1024 1024 "$PNG" --out "$ICONSET/icon_512x512@2x.png"

# Create .icns from iconset
iconutil -c icns "$ICONSET" -o "$ICNS"

rm -rf "$ICONSET"
echo "Created: $ICNS"
