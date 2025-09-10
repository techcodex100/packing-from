#!/bin/bash
set -e

echo "Starting build process..."

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements using wheels only to avoid Rust/maturin builds
export PIP_PREFER_BINARY=1

echo "Installing Python dependencies (wheels only)..."
pip install --no-cache-dir --only-binary=:all: -r requirements.txt

echo "Build completed successfully!"
