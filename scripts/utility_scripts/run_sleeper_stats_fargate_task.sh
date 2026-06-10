#!/bin/bash
set -euo pipefail

# Launch the Sleeper player stats refresher Fargate task (BE-011) on demand.
# The task otherwise runs on a weekly CloudWatch Events schedule.
#
# Usage: ./run_sleeper_stats_fargate_task.sh [env] [region] [season]
#   env     dev | prod   (default: dev)
#   region  AWS region    (default: us-east-1)
#   season  optional season override (e.g. 2024). When set, forces a refresh for that
#           season and bypasses the live NFL-state check (including the off-season skip);
#           omit for full production behavior.
#
# Prerequisites:
#   - The image is pushed to ECR and the task definition is registered (post-CI deploy).
#   - The shared Fargate VPC exists (created in the aws-account-management repo).

ENV="${1:-dev}"
REGION="${2:-us-east-1}"
SEASON="${3:-}"

# Resolve the shared Fargate networking by tag (same tags Terraform filters on).
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" \
  --filters "Name=tag:Name,Values=leagueql-fargate-vpc" \
  --query 'Vpcs[0].VpcId' --output text)

SUBNETS=$(aws ec2 describe-subnets --region "$REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:tier,Values=public" \
  --query 'Subnets[].SubnetId' --output text | tr '\t' ',')

SG=$(aws ec2 describe-security-groups --region "$REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=leagueql-fargate-task-sg" \
  --query 'SecurityGroups[0].GroupId' --output text)

# An explicit season is passed as a SEASON container env override; otherwise the task
# runs with no overrides (full production behavior).
OVERRIDES=()
if [[ -n "$SEASON" ]]; then
  OVERRIDES=(--overrides "{
    \"containerOverrides\": [{
      \"name\": \"sleeper-player-stats-refresher\",
      \"environment\": [{\"name\": \"SEASON\", \"value\": \"$SEASON\"}]
    }]
  }")
fi

# Run the task. assignPublicIp=ENABLED is required: the task lives in a public subnet
# with no NAT, so it needs a public IP to reach the Sleeper API.
aws ecs run-task --region "$REGION" \
  --cluster "leagueql-$ENV" \
  --task-definition "leagueql-sleeper-player-stats-refresher-$ENV" \
  --launch-type FARGATE \
  --count 1 \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=ENABLED}" \
  ${OVERRIDES[@]+"${OVERRIDES[@]}"}
