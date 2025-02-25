#!/bin/bash

PERSISTENT_PATH="/home/site/wwwroot"
SCRIPT_NAME="demo.sh"

# If script is running from /tmp, move it to persistent storage
if [[ "$0" == /tmp/* ]]; then
    echo "Moving $SCRIPT_NAME to persistent storage..." 
    cp "$0" "$PERSISTENT_PATH/$SCRIPT_NAME"
    chmod +x "$PERSISTENT_PATH/$SCRIPT_NAME"
    exec "$PERSISTENT_PATH/$SCRIPT_NAME" # Restart script from new location
    exit  # Prevent further execution from /tmp
fi

# Your actual installation & startup commands
echo "Running demo.sh from persistent storage..."
apt-get update && apt-get install -y libreoffice
exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
