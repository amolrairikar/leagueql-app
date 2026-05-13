#!/bin/bash
# Script to configure AWS credentials using OIDC (GitHub Actions)
# Usage: configure_aws_credentials.sh <role_arn> <aws_region> <session_name>
# Requires: AWS CLI v2, jq

set -e

ROLE_ARN=$1
AWS_REGION=$2
SESSION_NAME=$3

if [ -z "$ROLE_ARN" ] || [ -z "$AWS_REGION" ] || [ -z "$SESSION_NAME" ]; then
  echo "Error: Missing required arguments"
  echo "Usage: configure_aws_credentials.sh <role_arn> <aws_region> <session_name>"
  exit 1
fi

echo "Configuring AWS credentials for role: ${ROLE_ARN}"
echo "Region: ${AWS_REGION}"
echo "Session name: ${SESSION_NAME}"

# Get the OIDC token from GitHub Actions
# GitHub provides the OIDC token via ACTIONS_ID_TOKEN_REQUEST_TOKEN and ACTIONS_ID_TOKEN_REQUEST_URL
if [ -z "$ACTIONS_ID_TOKEN_REQUEST_TOKEN" ] || [ -z "$ACTIONS_ID_TOKEN_REQUEST_URL" ]; then
  echo "Error: OIDC token environment variables not found. This script must run in GitHub Actions with id-token: write permission."
  exit 1
fi

# Request the OIDC token
OIDC_TOKEN=$(curl -s -H "Authorization: bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" \
  "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=sts.amazonaws.com" | jq -r '.value')

if [ -z "$OIDC_TOKEN" ] || [ "$OIDC_TOKEN" == "null" ]; then
  echo "Error: Failed to retrieve OIDC token"
  exit 1
fi

# Assume the role using web identity
CREDENTIALS=$(aws sts assume-role-with-web-identity \
  --role-arn "${ROLE_ARN}" \
  --role-session-name "${SESSION_NAME}" \
  --web-identity-token "${OIDC_TOKEN}" \
  --duration-seconds 3600 \
  --region "${AWS_REGION}")

# Extract credentials
AWS_ACCESS_KEY_ID=$(echo "$CREDENTIALS" | jq -r '.Credentials.AccessKeyId')
AWS_SECRET_ACCESS_KEY=$(echo "$CREDENTIALS" | jq -r '.Credentials.SecretAccessKey')
AWS_SESSION_TOKEN=$(echo "$CREDENTIALS" | jq -r '.Credentials.SessionToken')

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ "$AWS_ACCESS_KEY_ID" == "null" ]; then
  echo "Error: Failed to assume role"
  echo "$CREDENTIALS"
  exit 1
fi

# Export credentials to environment
echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}" >> $GITHUB_ENV
echo "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}" >> $GITHUB_ENV
echo "AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}" >> $GITHUB_ENV
echo "AWS_REGION=${AWS_REGION}" >> $GITHUB_ENV
echo "AWS_DEFAULT_REGION=${AWS_REGION}" >> $GITHUB_ENV

# Also set for current shell session
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN
export AWS_REGION
export AWS_DEFAULT_REGION

echo "AWS credentials configured successfully"
