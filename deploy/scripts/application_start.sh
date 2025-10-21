#!/bin/bash
set -e

echo "Starting application_start hook"

# Run database migrations
echo "Running database migrations..."
aws ecs run-task \
  --cluster meal-planner-cluster \
  --task-definition meal-planner-production \
  --overrides '{"containerOverrides":[{"name":"meal-planner","command":["python","manage.py","migrate"]}]}' \
  --network-configuration "awsvpcConfiguration={subnets=[\"subnet-12345\",\"subnet-67890\"],securityGroups=[\"sg-12345\"]}"

# Wait for migration to complete
echo "Waiting for migrations to complete..."
sleep 60

echo "application_start hook completed"