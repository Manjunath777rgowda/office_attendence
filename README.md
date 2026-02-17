This **README** is tailored specifically for your macOS setup, detailing how the background tracking, notifications, and dashboard work together.

---

# 🏢 macOS Office Attendance Tracker

An automated, background Wi-Fi tracking system built for macOS. It monitors your Wi-Fi connections, logs the duration of each session in an SQLite database, and provides a web dashboard to track your 12-day-per-month office goal.

## 🌟 Features

* **Automatic Background Tracking:** Runs as a macOS `LaunchAgent`. Starts automatically when you log in.
* **Smart Notifications:** Sends native macOS desktop alerts when you connect to the office Wi-Fi, lose connection, or switch networks.
* **Configurable Goals:** Easily change your target SSID (Office Wi-Fi) and monthly day goals via a `config.json` file.
* **Universal Logging:** Logs *every* network you connect to, then filters the "Office" logs for your attendance summary.
* **Web Dashboard:** A clean, local interface to view your office history and "days remaining" at a glance.

---

## 🛠️ System Requirements

* **OS:** macOS (Tested on Monterey, Ventura, and Sonoma).
* **Python:** 3.x (Uses built-in `venv` and `sqlite3`).
* **Permissions:** Requires "Notifications" and "Automation" permissions (macOS will prompt you).

---

## 📂 Project Structure

```text
OfficeAttendance/
├── app.py              # Main Flask application & Background tracker
├── config.json         # Settings (Target SSID, Goal, Interface)
├── wifi_history.db     # SQLite database (auto-generated)
├── install_service.sh  # Setup & Start background service
├── stop_service.sh     # Stop & Disable background service
└── templates/
    └── index.html      # Dashboard UI

```

---

## 🚀 Installation & Setup

1. **Configure your settings:**
Edit `config.json` with your office details:
```json
{
    "target_ssid": "Airtel_manjunath",
    "monthly_goal": 12,
    "interface": "en0"
}

```


2. **Run the Installer:**
Open Terminal in the project folder and run:
```bash
chmod +x install_service.sh stop_service.sh
./install_service.sh

```


3. **Grant Permissions:**
When the first notification appears, click **Allow** to let the script send alerts.

---

## 📊 Usage

### Accessing the Dashboard

Open your browser and go to:
👉 **[http://127.0.0.1:5000]()**

### Managing the Service

* **To Stop Tracking:** `./stop_service.sh`
* **To Restart/Update:** `./install_service.sh`
* **View Live Logs:** `tail -f output.log` (In the app directory)

---

## 🔔 Notification Types

* **🚀 Service Started:** Sent when the Mac boots or the service is launched.
* **🌐 Wi-Fi Connected:** Sent whenever you join a network.
* **📍 Office Joined:** Specific alert when joining your `target_ssid`.
* **⚠️ Wi-Fi Offline:** Sent if Wi-Fi is turned off or the signal is lost.
* **🛑 Service Stopped:** Sent when you manually stop the tracker.

---

## 📋 Troubleshooting (macOS Specific)

* **No Notifications?** Ensure **System Settings > Notifications > Script Editor** (or Python) is allowed. Ensure "Do Not Disturb" is OFF.
* **Wrong Wi-Fi info?** Some Macs use `en1` instead of `en0`. Check `networksetup -listallhardwareports` and update `config.json`.
* **Database View:** You can view `wifi_history.db` directly in VS Code using the **SQLite Viewer** extension.

---
