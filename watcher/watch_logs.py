import os, time, re, sys
from collections import deque
from datetime import datetime, timedelta
import requests

LOG_PATH = os.getenv("LOG_PATH", "/var/log/nginx/access.log")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()
ERROR_RATE_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", "2.0")) 
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", "200"))  
ALERT_COOLDOWN_SEC = int(os.getenv("ALERT_COOLDOWN_SEC", "300"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "0.2"))
MAINTENANCE_MODE_ENV = os.getenv("MAINTENANCE_MODE", "false").lower() in ("1","true","yes")
MAINTENANCE_FILE = os.getenv("MAINTENANCE_FILE", "/app/maintenance/maintenance.flag")
QUIET = os.getenv("QUIET", "false").lower() in ("1","true","yes")


LINE_RE = re.compile(
    r'pool="(?P<pool>[^"]*)" .* release="(?P<release>[^"]*)" .* upstream_status="(?P<upstream_status>[^"]*)" .* upstream_addr="(?P<upstream_addr>[^"]*)" .* request_time=(?P<request_time>[\d.]+) upstream_response_time=(?P<upstream_response_time>[\d.\-]+)'
)

def send_slack(text):
    if MAINTENANCE_MODE_ENV or os.path.exists(MAINTENANCE_FILE):
        if not QUIET:
            print("[watcher] maintenance mode active - skipping alert:", text)
        return
    if not SLACK_WEBHOOK_URL:
        print("[watcher] no SLACK_WEBHOOK_URL configured; would send:", text)
        return
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
        if r.status_code >= 400:
            print("[watcher] slack send failed", r.status_code, r.text)
    except Exception as e:
        print("[watcher] slack error:", e)

def tail_file(path):
    # wait until file exists
    while not os.path.exists(path):
        if not QUIET:
            print(f"[watcher] waiting for log at {path}")
        time.sleep(0.5)
    f = open(path, "r")
    # go to end for live tailing
    f.seek(0, 2)
    inode = os.fstat(f.fileno()).st_ino
    while True:
        line = f.readline()
        if not line:
            # handle rotation: if inode changed, reopen
            try:
                if os.stat(path).st_ino != inode:
                    f.close()
                    f = open(path, "r")
                    inode = os.fstat(f.fileno()).st_ino
                    continue
            except FileNotFoundError:
                pass
            time.sleep(POLL_INTERVAL)
            continue
        yield line.rstrip("\n")

def parse_line(line):
    m = LINE_RE.search(line)
    if not m:
        return None
    info = m.groupdict()
    upstream_status = info.get("upstream_status") or ""
    status_codes = [int(s) for s in re.findall(r'\d{3}', upstream_status)]
    last_status = status_codes[-1] if status_codes else None
    info['last_status'] = last_status
    info['ts'] = datetime.utcnow()
    return info

def main():
    last_pool = None
    last_alert_ts = {"failover": None, "error_rate": None}
    window = deque(maxlen=WINDOW_SIZE)  # store booleans: True if 5xx, else False

    for raw in tail_file(LOG_PATH):
        parsed = parse_line(raw)
        if not parsed:
            continue

        pool = parsed.get("pool") or "unknown"
        status = parsed.get("last_status")
        is_5xx = (status is not None and 500 <= status <= 599)

        window.append(is_5xx)
        total = len(window)
        errors = sum(1 for e in window if e)
        error_rate = (errors / total * 100) if total > 0 else 0.0

        # failover detection
        if last_pool is None:
            last_pool = pool

        if pool != last_pool:
            now = datetime.utcnow()
            last = last_alert_ts["failover"]
            if (last is None) or ((now - last).total_seconds() >= ALERT_COOLDOWN_SEC):
                send_slack(f":rotating_light: Failover detected: {last_pool} → {pool} at {now.isoformat()} (latest_status={status})")
                last_alert_ts["failover"] = now
            last_pool = pool

        # error-rate detection
        now = datetime.utcnow()
        last_er = last_alert_ts["error_rate"]
        if total >= 1 and total >= WINDOW_SIZE and error_rate >= ERROR_RATE_THRESHOLD:
            if (last_er is None) or ((now - last_er).total_seconds() >= ALERT_COOLDOWN_SEC):
                send_slack(f":warning: Elevated 5xx error rate: {error_rate:.2f}% ({errors}/{total}) over last {WINDOW_SIZE} requests. latest_pool={pool}, latest_status={status}")
                last_alert_ts["error_rate"] = now

        if not QUIET:
            print(f"[{datetime.utcnow().isoformat()}] pool={pool} status={status} window={total} 5xx={errors} rate={error_rate:.2f}%")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
