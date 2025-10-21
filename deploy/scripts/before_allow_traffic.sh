#!/bin/bash
set -e

echo "Starting before_allow_traffic hook"

# Health check before allowing traffic
HEALTH_CHECK_URL="http://localhost:8000/health/"
MAX_ATTEMPTS=20
ATTEMPT=1

echo "Performing health checks..."
while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if curl -f $HEALTH_CHECK_URL; then
        echo "Health check passed on attempt $ATTEMPT"
        break
    else
        echo "Health check failed on attempt $ATTEMPT/$MAX_ATTEMPTS"
        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo "Health check failed after $MAX_ATTEMPTS attempts"
            exit 1
        fi
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 30
done

echo "before_allow_traffic hook completed"