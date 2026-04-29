#!/bin/bash
# Script to set up a specific Python version
# Usage: setup_python.sh <python_version>
# Example: setup_python.sh "3.13"

set -e

PYTHON_VERSION=$1

if [ -z "$PYTHON_VERSION" ]; then
  echo "Error: Python version not specified"
  echo "Usage: setup_python.sh <python_version>"
  exit 1
fi

echo "Setting up Python ${PYTHON_VERSION}..."

# Check if the requested version is already available
PYTHON_BIN="python${PYTHON_VERSION}"

if command -v "$PYTHON_BIN" &> /dev/null; then
  echo "Python ${PYTHON_VERSION} is already available at $(which $PYTHON_BIN)"
else
  echo "Python ${PYTHON_VERSION} not found, attempting to install..."
  
  # Detect OS
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
  else
    echo "Error: Cannot detect OS"
    exit 1
  fi

  if [ "$OS" == "ubuntu" ]; then
    echo "Installing Python ${PYTHON_VERSION} on Ubuntu..."
    
    # Add deadsnakes PPA if not already added
    if ! grep -q "deadsnakes" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null; then
      echo "Adding deadsnakes PPA..."
      sudo apt-get update
      sudo apt-get install -y software-properties-common
      sudo add-apt-repository -y ppa:deadsnakes/ppa
    fi
    
    # Update package list
    sudo apt-get update
    
    # Install Python and dev packages
    sudo apt-get install -y "$PYTHON_BIN" "$PYTHON_BIN"-dev "$PYTHON_BIN"-venv
    
    # Install pip using ensurepip (built into Python)
    sudo "$PYTHON_BIN" -m ensurepip --upgrade --default-pip
  else
    echo "Error: Unsupported OS: $OS"
    echo "This script currently only supports Ubuntu"
    exit 1
  fi
fi

# Verify installation
if command -v "$PYTHON_BIN" &> /dev/null; then
  INSTALLED_VERSION=$($PYTHON_BIN --version)
  echo "Successfully set up Python: $INSTALLED_VERSION"
  
  # Add to PATH and export to GITHUB_ENV
  PYTHON_DIR=$(dirname $(which $PYTHON_BIN))
  echo "$PYTHON_DIR" >> $GITHUB_PATH
  echo "Added $PYTHON_DIR to PATH"
  
  # Set PYTHON environment variables
  echo "PYTHON_VERSION=${PYTHON_VERSION}" >> $GITHUB_ENV
  echo "PYTHON=${PYTHON_BIN}" >> $GITHUB_ENV
  echo "PYTHON_PATH=$(which $PYTHON_BIN)" >> $GITHUB_ENV
  
  # Also set for current shell
  export PATH="$PYTHON_DIR:$PATH"
  export PYTHON_VERSION="$PYTHON_VERSION"
  export PYTHON="$PYTHON_BIN"
  export PYTHON_PATH="$(which $PYTHON_BIN)"
  
  # Display version
  $PYTHON_BIN --version
else
  echo "Error: Failed to set up Python ${PYTHON_VERSION}"
  exit 1
fi
