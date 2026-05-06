import logging
import subprocess
import sqlite3
import time
import threading
import json
import os
import signal
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
DB_NAME = "wifi_history.db"
CONFIG_FILE = "config.json"
last_ssid = None  # Global to track state changes

logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
# --- NOTIFICATIONS & SIGNALS ---
def send_notification(title, message):
    try:
        script = f"""
        tell application "System Events"
            activate
            display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"
        end tell
        """
        print("Sending Notification:", title, message)
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
    logging.info("--- Tracker Started ---")
    logging.info("---Last Ran at ---> %s", datetime.now())
    config = load_config()
    now = datetime.now()
    current_ssid = get_current_ssid(config["interface"])

    logging.info(f"Current SSID: {current_ssid}, Last SSID: {last_ssid}")
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
    # logging.info("---Sleeping for 60 seconds---")
    # # time.sleep(60)
    # logging.info("---Woke up at ---> %s", datetime.now())


# --- DATA AGGREGATION FUNCTIONS ---
def get_monthly_report(office_ssid, monthly_goal):
    """Get monthly attendance report for the past 12 months with goal tracking"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        monthly_data = conn.execute(
            """
            SELECT
                strftime('%Y-%m', date) as month,
                COUNT(DISTINCT date) as days_present,
                SUM(duration_mins) as total_minutes
            FROM daily_logs
            WHERE ssid = ?
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month DESC
            LIMIT 12
            """,
            (office_ssid,),
        ).fetchall()

    # Add goal tracking to each month
    monthly_with_goals = []
    for row in monthly_data:
        row_dict = dict(row)
        row_dict["goal"] = monthly_goal
        row_dict["days_remaining"] = max(0, monthly_goal - row_dict["days_present"])
        monthly_with_goals.append(row_dict)

    return monthly_with_goals


def get_quarterly_report(office_ssid, quarterly_goal):
    """Get quarterly attendance report with goal tracking"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        quarterly_data = conn.execute(
            """
            SELECT
                CASE
                    WHEN CAST(strftime('%m', date) AS INTEGER) BETWEEN 1 AND 3 THEN strftime('%Y', date) || '-Q1'
                    WHEN CAST(strftime('%m', date) AS INTEGER) BETWEEN 4 AND 6 THEN strftime('%Y', date) || '-Q2'
                    WHEN CAST(strftime('%m', date) AS INTEGER) BETWEEN 7 AND 9 THEN strftime('%Y', date) || '-Q3'
                    ELSE strftime('%Y', date) || '-Q4'
                END as quarter,
                COUNT(DISTINCT date) as days_present,
                SUM(duration_mins) as total_minutes
            FROM daily_logs
            WHERE ssid = ?
            GROUP BY quarter
            ORDER BY quarter DESC
            LIMIT 8
            """,
            (office_ssid,),
        ).fetchall()

    # Add goal tracking to each quarter
    quarterly_with_goals = []
    for row in quarterly_data:
        row_dict = dict(row)
        row_dict["goal"] = quarterly_goal
        row_dict["days_remaining"] = max(0, quarterly_goal - row_dict["days_present"])
        quarterly_with_goals.append(row_dict)

    return quarterly_with_goals


# --- WEB ROUTES ---
@app.route("/")
def index():
    config = load_config()
    office_ssid = config["target_ssid"]
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        office_history = conn.execute(
            "SELECT * FROM daily_logs WHERE ssid = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime') ORDER BY date DESC",
            (office_ssid,),
        ).fetchall()
        other_history = conn.execute(
            "SELECT * FROM daily_logs WHERE ssid != ? ORDER BY date DESC",
            (office_ssid,),
        ).fetchall()
        completed = len(office_history)
        remaining = max(0, config["monthly_goal"] - completed)

    # Get monthly and quarterly reports
    monthly_report = get_monthly_report(office_ssid, config["monthly_goal"])
    quarterly_goal = config["monthly_goal"] * 3  # Quarterly goal is 3x monthly goal
    quarterly_report = get_quarterly_report(office_ssid, quarterly_goal)

    # Calculate current quarter's days left
    now = datetime.now()
    current_quarter = f"{now.year}-Q{((now.month - 1) // 3) + 1}"
    quarterly_completed = 0
    for row in quarterly_report:
        if row["quarter"] == current_quarter:
            quarterly_completed = row["days_present"]
            break
    quarterly_remaining = max(0, quarterly_goal - quarterly_completed)

    return render_template(
        "index.html",
        office_history=office_history,
        other_history=other_history,
        completed=completed,
        remaining=remaining,
        office_ssid=office_ssid,
        goal=config["monthly_goal"],
        monthly_report=monthly_report,
        quarterly_report=quarterly_report,
        quarterly_goal=quarterly_goal,
        quarterly_completed=quarterly_completed,
        quarterly_remaining=quarterly_remaining,
    )


@app.route("/api/monthly-report")
def api_monthly_report():
    """API endpoint for monthly report data"""
    config = load_config()
    office_ssid = config["target_ssid"]
    monthly_data = get_monthly_report(office_ssid, config["monthly_goal"])
    return jsonify(monthly_data)


@app.route("/api/quarterly-report")
def api_quarterly_report():
    """API endpoint for quarterly report data"""
    config = load_config()
    office_ssid = config["target_ssid"]
    quarterly_goal = config["monthly_goal"] * 3
    quarterly_data = get_quarterly_report(office_ssid, quarterly_goal)
    return jsonify(quarterly_data)


scheduler = BackgroundScheduler()
scheduler.add_job(tracker_loop, "interval", seconds=60)
scheduler.start()

if __name__ == "__main__":
    init_db()
    send_notification("Office Tracker", "🚀 Background Service Started.")
    # threading.Thread(target=tracker_loop, daemon=True).start()
    app.run(port=5000, debug=False, use_reloader=False)
