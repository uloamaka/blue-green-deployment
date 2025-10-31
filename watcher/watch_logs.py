#!/usr/bin/env python3
import os
import time
import random
import datetime
import requests

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))
ERROR_THRESHOLD = float(os.getenv("ERROR_THRESHOLD", "0.8"))

CURRENT_POOL = "blue"
ERROR_RATE = 0.0

def send_slack_alert(title, fields, color, footer=None):
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title}
        },
        {
            "type": "section",
            "fields": [{"type": "mrkdwn", "text": f"*{k}:*\n{v}"} for k, v in fields.items()]
        }
    ]
    if footer:
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": footer}]
            }
        )
    payload = {
        "blocks": blocks,
        "attachments": [
            {
                "color": color
            }
        ]
    }
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        if response.status_code != 200:
            print(f"Slack API error: {response.text}")
    except Exception as e:
        print(f"Error sending Slack alert: {e}")

def high_error_alert(error_rate, window):
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    send_slack_alert(
        title=":rotating_light: High Error Rate Detected",
        fields={
            "Error Rate": f"{error_rate * 100:.2f}%",
            "Window": f"{window[0]}/{window[1]} requests",
            "Timestamp": timestamp,
            "Action Required": "Inspect upstream logs and consider pool toggle"
        },
        color="#E01E5A",
        footer="Source: Nginx Log Watcher"
    )

def failover_alert(from_pool, to_pool):
    send_slack_alert(
        title="Nginx Alert: Failover",
        fields={
            "Status": f"FAILOVER DETECTED: Traffic has flipped from *'{from_pool}'* to *'{to_pool}'*.",
            "Action": f"The primary pool ({from_pool}) has failed. Check its logs (`docker logs app_{from_pool}`) to investigate."
        },
        color="#ECB22E",
        footer="Source: Nginx Blue/Green Watcher"
    )

def recovery_alert(from_pool, to_pool):
    send_slack_alert(
        title="Nginx Alert: Recovery",
        fields={
            "Status": f"RECOVERY: Traffic has flipped from *'{from_pool}'* back to *'{to_pool}'*.",
            "Action": f"This is a recovery notification. The primary pool ({to_pool}) is healthy again and serving traffic."
        },
        color="#2EB67D",
        footer="Source: Nginx Blue/Green Watcher"
    )

def check_error_rate():
    total = random.randint(50, 100)
    errors = random.randint(0, total)
    return errors / total, (errors, total)

def main():
    global CURRENT_POOL, ERROR_RATE
    print("🚀 Starting nginx alert watcher...")
    while True:
        error_rate, window = check_error_rate()
        ERROR_RATE = error_rate
        print(f"[Watcher] Current error rate: {error_rate:.2%}")
        if error_rate > ERROR_THRESHOLD:
            high_error_alert(error_rate, window)
            if CURRENT_POOL == "blue":
                failover_alert("blue", "green")
                CURRENT_POOL = "green"
            else:
                failover_alert("green", "blue")
                CURRENT_POOL = "blue"
        elif error_rate < 0.2 and CURRENT_POOL != "blue":
            recovery_alert("green", "blue")
            CURRENT_POOL = "blue"
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    if not SLACK_WEBHOOK_URL:
        print("❌ Missing SLACK_WEBHOOK_URL environment variable.")
        exit(1)
    main()
