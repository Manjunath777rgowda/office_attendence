import subprocess
import sqlite3
import time
import threading
import json
import os
import signal
import sys
from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)
DB_NAME = "wifi_history.db"
CONFIG_FILE = "config.json"
last_ssid = None  # Global to track state changes


# --- NOTIFICATIONS & SIGNALS ---
def send_notification(title, message):
    try:
        script = f"""
        tell application "System Events"
            activate
            display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"
        end tell
        """
        subprocess.run(["osascript", "-e", script])
    except Exception as e:
        print("Notification Error:", e)


def signal_handler(sig, frame):
    send_notification("Office Tracker", "🛑 Service has been stopped.")
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)


# --- UTILITIES ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "target_ssid": "Airtel_manjunath",
            "monthly_goal": 12,
            "interface": "en0",
        }
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS daily_logs 
            (date TEXT, ssid TEXT, duration_mins INTEGER, PRIMARY KEY (date, ssid))"""
        )


def get_current_ssid(interface):
    try:
        cmd = f"ipconfig getsummary {interface} | grep ' SSID' | awk -F': ' '{{print $2}}'"
        ssid = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        return ssid if ssid else None
    except:
        return None


# --- TRACKER LOOP ---
def tracker_loop():
    global last_ssid
    print("--- Tracker Started ---")
    while True:
        config = load_config()
        now = datetime.now()
        current_ssid = get_current_ssid(config["interface"])

        if current_ssid is None:
            send_notification("Wi-fi Disconnected", "Wi-fi Disconnected")
            return
        # Connection/Disconnection Logic
        if current_ssid and last_ssid is None:
            send_notification("Wi-Fi Connected", f"🌐 Joined {current_ssid}")
        elif last_ssid and current_ssid is None:
            send_notification("Wi-Fi Offline", "⚠️ Wi-Fi is turned off or lost.")
        elif current_ssid and last_ssid and current_ssid != last_ssid:
            send_notification("Network Switched", f"🔄 Moved to {current_ssid}")

        # Logging Logic
        if current_ssid:
            today = now.strftime("%Y-%m-%d")
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT duration_mins FROM daily_logs WHERE date=? AND ssid=?",
                    (today, current_ssid),
                )
                row = cursor.fetchone()
                if not row:
                    cursor.execute(
                        "INSERT INTO daily_logs VALUES (?, ?, ?)",
                        (today, current_ssid, 1),
                    )
                else:
                    cursor.execute(
                        "UPDATE daily_logs SET duration_mins=? WHERE date=? AND ssid=?",
                        (row[0] + 1, today, current_ssid),
                    )
                conn.commit()

        last_ssid = current_ssid
        time.sleep(60)


# --- WEB ROUTES ---
@app.route("/")
def index():
    config = load_config()
    office_ssid = config["target_ssid"]
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        office_history = conn.execute(
            "SELECT * FROM daily_logs WHERE ssid = ? ORDER BY date DESC", (office_ssid,)
        ).fetchall()
        other_history = conn.execute(
            "SELECT * FROM daily_logs WHERE ssid != ? ORDER BY date DESC",
            (office_ssid,),
        ).fetchall()
        completed = len(office_history)
        remaining = max(0, config["monthly_goal"] - completed)
    return render_template(
        "index.html",
        office_history=office_history,
        other_history=other_history,
        completed=completed,
        remaining=remaining,
        office_ssid=office_ssid,
        goal=config["monthly_goal"],
    )


if __name__ == "__main__":
    init_db()
    send_notification("Office Tracker", "🚀 Background Service Started.")
    threading.Thread(target=tracker_loop, daemon=True).start()
    app.run(port=5000, debug=False, use_reloader=False)
