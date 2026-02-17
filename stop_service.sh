#!/bin/bash

PLIST_NAME="com.user.office_tracker"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "--- 🛑 Stopping Office Attendance Service ---"

# 1. Unload the service from launchctl
if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH"
    echo "Service unloaded from LaunchAgents."
else
    echo "Service file not found at $PLIST_PATH"
fi

# 2. Force kill any remaining python processes just in case
# This looks for the specific app.py process
PID=$(ps aux | grep 'app.py' | grep -v 'grep' | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "Cleaning up lingering process (PID: $PID)..."
    kill -9 $PID
else
    echo "No background python processes found."
fi

echo "------------------------------------------------"
echo "✅ Service Stopped Successfully."
echo "The dashboard at http://localhost:5000 is now offline."
echo "------------------------------------------------"