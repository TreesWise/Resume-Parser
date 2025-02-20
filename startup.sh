#!/bin/bash

echo "🔄 Updating system and installing fonts..."

# Install fontconfig and necessary fonts
apk add --no-cache fontconfig ttf-dejavu ttf-liberation

# Rebuild font cache
fc-cache -fv

echo "✅ Fonts installed successfully!"

# Start the FastAPI application using Gunicorn
exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
