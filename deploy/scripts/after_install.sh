#!/bin/bash
set -e

echo "Starting after_install hook"

# Wait for task to be running
echo "Waiting for new tasks to be running..."
sleep 30

echo "after_install hook completed"