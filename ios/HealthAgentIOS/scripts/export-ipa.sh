#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_PATH="$ROOT_DIR/HealthAgentIOS.xcodeproj"
SCHEME="HealthAgentIOS"
ARCHIVE_PATH="${ARCHIVE_PATH:-$ROOT_DIR/build/HealthAgentIOS.xcarchive}"
EXPORT_PATH="${EXPORT_PATH:-$ROOT_DIR/build/export}"
EXPORT_OPTIONS_PLIST="${EXPORT_OPTIONS_PLIST:-$ROOT_DIR/export/ExportOptions.ad-hoc.plist}"
CONFIGURATION="${CONFIGURATION:-Release}"

mkdir -p "$(dirname "$ARCHIVE_PATH")" "$EXPORT_PATH"

echo "Archiving $SCHEME..."
xcodebuild \
  -project "$PROJECT_PATH" \
  -scheme "$SCHEME" \
  -configuration "$CONFIGURATION" \
  -destination "generic/platform=iOS" \
  -archivePath "$ARCHIVE_PATH" \
  archive

echo "Exporting IPA..."
xcodebuild \
  -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_PATH" \
  -exportOptionsPlist "$EXPORT_OPTIONS_PLIST"

echo
echo "Done."
echo "Archive: $ARCHIVE_PATH"
echo "Export:  $EXPORT_PATH"
