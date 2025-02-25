#!/bin/bash

# Define paths
PERSISTENT_PATH="/home/site/wwwroot"
DEMO_SCRIPT="$PERSISTENT_PATH/demo.sh"

# Ensure the persistent directory exists
mkdir -p $PERSISTENT_PATH

# Search for the demo.sh script in /tmp/ and move it to a persistent location
if [ ! -f "$DEMO_SCRIPT" ]; then
    echo "Looking for demo.sh in /tmp/..."
    TEMP_DEMO_PATH=$(find /tmp -type f -name "demo.sh" 2>/dev/null | head -n 1)

    if [ -n "$TEMP_DEMO_PATH" ]; then
        echo "Copying demo.sh to persistent path: $PERSISTENT_PATH"
        cp "$TEMP_DEMO_PATH" "$DEMO_SCRIPT"
        chmod +x "$DEMO_SCRIPT"
    else
        echo "ERROR: demo.sh not found in /tmp/. Exiting."
        exit 1
    fi
fi

# Ensure requirements.txt exists before trying to install dependencies
if [ -f "$PERSISTENT_PATH/requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r "$PERSISTENT_PATH/requirements.txt" &
else
    echo "WARNING: requirements.txt not found, skipping dependency installation."
fi

# Start Uvicorn using Gunicorn
echo "Starting FastAPI application..."
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
