#!/bin/bash

# 1. Get current directory and user info
APP_DIR=$(pwd)
USER_NAME=$(whoami)
PLIST_NAME="com.user.office_tracker"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "--- 🚀 Office Attendance Background Setup ---"

# 2. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install Flask==3.0.0

# 3. Create the LaunchAgent Plist
echo "Generating background service configuration..."
cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$APP_DIR/venv/bin/python3</string>
        <string>$APP_DIR/app.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$APP_DIR</string>
    <key>StandardOutPath</key>
    <string>$APP_DIR/output.log</string>
    <key>StandardErrorPath</key>
    <string>$APP_DIR/error.log</string>
</dict>
</plist>
EOF

# 4. Load the Service
echo "Activating service..."
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo "------------------------------------------------"
echo "✅ SETUP COMPLETE!"
echo "Dashboard: http://localhost:5000"
echo "Logs: tail -f output.log"
echo "------------------------------------------------"