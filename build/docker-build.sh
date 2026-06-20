#!/usr/bin/env bash
# docker-build.sh — Build standalone binary in Ubuntu 22.04 container (GLIBC 2.35)
# Compatible with any Linux distribution with GLIBC >= 2.35
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

IMAGE="mc-config-editor-builder"

echo "==> Building Docker image (Ubuntu 22.04, GLIBC 2.35)..."
docker build -t "$IMAGE" -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_DIR"

echo "==> Building binary in container..."
docker run --rm \
    -v "$PROJECT_DIR":/build \
    "$IMAGE"

echo "==> Done! Binary: $PROJECT_DIR/dist/mc-config-editor"
