#!/bin/bash

# Define paths
PERSISTENT_PATH="/home/site/wwwroot"
DEMO_SCRIPT="demo.sh"

# Ensure the persistent directory exists
mkdir -p $PERSISTENT_PATH

# Find demo.sh dynamically inside /tmp/ (in case the temp folder name changes)
TEMP_DEMO_PATH=$(find /tmp -type f -name "$DEMO_SCRIPT" 2>/dev/null | head -n 1)

# If demo.sh is found in temp, move it to the persistent path
if [ -n "$TEMP_DEMO_PATH" ]; then
    cp "$TEMP_DEMO_PATH" "$PERSISTENT_PATH/$DEMO_SCRIPT"
fi

# Ensure demo.sh has execution permissions
chmod +x "$PERSISTENT_PATH/$DEMO_SCRIPT"

# Run demo.sh
/bin/bash "$PERSISTENT_PATH/$DEMO_SCRIPT"
# Start Uvicorn after setup
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
