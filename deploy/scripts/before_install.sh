#!/bin/bash
set -e

echo "Starting before_install hook"

# Log deployment start
aws logs put-log-events \
  --log-group-name "/aws/codedeploy/meal-planner" \
  --log-stream-name "deployment-$(date +%Y%m%d-%H%M%S)" \
  --log-events timestamp=$(date +%s)000,message="Deployment started"

echo "before_install hook completed"