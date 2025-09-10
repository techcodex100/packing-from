#!/bin/bash
set -e

echo "Starting build process..."

# Set environment variables to avoid compilation issues
export PIP_NO_BUILD_ISOLATION=1
export PIP_NO_CACHE_DIR=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements with specific flags to avoid compilation issues
echo "Installing Python dependencies..."
pip install --no-cache-dir --no-build-isolation -r requirements.txt

echo "Build completed successfully!"
