#!/bin/bash
set -e

echo "Starting after_allow_traffic hook"

# Run smoke tests
echo "Running smoke tests..."

# Test main endpoints
curl -f "https://meal-planner.example.com/" || exit 1
curl -f "https://meal-planner.example.com/accounts/login/" || exit 1
curl -f "https://meal-planner.example.com/health/" || exit 1

# Send deployment success notification
aws sns publish \
  --topic-arn "arn:aws:sns:us-east-1:ACCOUNT_ID:meal-planner-deployments" \
  --message "Deployment completed successfully" \
  --subject "Meal Planner - Deployment Success"

echo "after_allow_traffic hook completed"