#!/bin/bash
# Script to install a specific version of Terraform CLI
# Usage: setup_terraform.sh [terraform_version]
# If no version is specified, defaults to 1.14.7
# Periodically update the default version to the latest stable release

set -e

TERRAFORM_VERSION=${1:-"1.14.7"}
INSTALL_DIR="/usr/local/bin"

echo "Installing Terraform version ${TERRAFORM_VERSION}..."

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Map architecture names
case $ARCH in
  x86_64)
    ARCH="amd64"
    ;;
  aarch64|arm64)
    ARCH="arm64"
    ;;
  *)
    echo "Unsupported architecture: ${ARCH}"
    exit 1
    ;;
esac

# Construct download URL
DOWNLOAD_URL="https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_${OS}_${ARCH}.zip"

echo "Downloading Terraform from ${DOWNLOAD_URL}..."

# Download and install
TEMP_DIR=$(mktemp -d)
cd "${TEMP_DIR}"

curl -fsSL -o terraform.zip "${DOWNLOAD_URL}"
unzip -o terraform.zip
sudo mv terraform "${INSTALL_DIR}/terraform"
chmod +x "${INSTALL_DIR}/terraform"

# Cleanup
cd -
rm -rf "${TEMP_DIR}"

echo "Terraform ${TERRAFORM_VERSION} installed successfully to ${INSTALL_DIR}/terraform"
terraform --version
