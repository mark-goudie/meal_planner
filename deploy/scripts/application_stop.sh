#!/bin/bash
set -e

echo "Starting application_stop hook"

# Graceful shutdown - nothing specific needed for ECS
echo "Graceful shutdown initiated"

echo "application_stop hook completed"