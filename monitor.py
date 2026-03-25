import os
import json
import requests
from datetime import datetime, timezone

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
TARGET_URL = "https://www.pokemoncenter.com/"
STATUS_FILE = "docs/status.json"
MAX_HISTORY = 100

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

QUEUE_SIGNALS = [
    "queue-it.net", "queueit", "youarenext",
    "queueid", "waitingroom", "waiting room",
]

SECURITY_SIGNALS = [
    "cf-browser-verification", "checking your browser",
    "ddos protection by cloudflare", "enable javascript and cookies",
    "cf_chl_opt", "datadome", "_pxcaptcha", "perimeterx",
]


def notify(title, body, priority="high"):
    print(f"[ALERT] {title}: {body}")
    if not NTFY_TOPIC:
        return
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": "rotating_light,pokemon",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"ntfy send failed: {e}")


def load_history():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"current_status": "unknown", "last_updated": None, "checks": []}


def save_history(data):
    os.makedirs("docs", exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record(result):
    data = load_history()
    data["checks"].insert(0, result)
    data["checks"] = data["checks"][:MAX_HISTORY]
    data["last_updated"] = result["timestamp"]
    data["current_status"] = result["status"]
    save_history(data)


def check():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        resp = requests.get(TARGET_URL, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as e:
        msg = f"Could not connect: {e}"
        notify("Pokemon Center - Unreachable", msg, priority="default")
        record({"timestamp": now, "status": "error", "http_code": None, "message": msg, "alerts": []})
        return

    status_code = resp.status_code
    body = resp.text.lower()
    final_url = resp.url

    print(f"HTTP {status_code}  |  {final_url}")

    # Queue-It URL redirect
    if "queue-it.net" in final_url or "queueit" in final_url.lower():
        msg = "Queue-It redirect detected. Virtual queue is LIVE."
        notify("QUEUE ACTIVE - Pokemon Center", f"Get in line NOW!\n{TARGET_URL}", priority="urgent")
        record({"timestamp": now, "status": "queue", "http_code": status_code, "message": msg, "alerts": ["queue-it redirect"]})
        return

    # Queue-It in page body
    queue_hits = [s for s in QUEUE_SIGNALS if s in body]
    if queue_hits:
        msg = f"Virtual queue detected: {', '.join(queue_hits)}"
        notify("QUEUE ACTIVE - Pokemon Center", f"{msg}\n{TARGET_URL}", priority="urgent")
        record({"timestamp": now, "status": "queue", "http_code": status_code, "message": msg, "alerts": queue_hits})
        return

    # Bot-protection / security challenge
    sec_hits = [s for s in SECURITY_SIGNALS if s in body]
    if sec_hits:
        msg = f"Security challenge active: {', '.join(sec_hits)}"
        notify("Security Change - Pokemon Center", f"Drop may be imminent.\n{TARGET_URL}", priority="high")
        record({"timestamp": now, "status": "security", "http_code": status_code, "message": msg, "alerts": sec_hits})
        return

    # 503 often precedes a drop
    if status_code == 503:
        msg = "Site returned 503 — may be preparing for a drop."
        notify("503 - Pokemon Center", f"{msg}\n{TARGET_URL}", priority="high")
        record({"timestamp": now, "status": "security", "http_code": 503, "message": msg, "alerts": ["503"]})
        return

    # Any other unexpected status
    if status_code not in (200, 301, 302, 304):
        msg = f"Unexpected HTTP {status_code}"
        notify(f"Status {status_code} - Pokemon Center", f"{msg}\n{TARGET_URL}", priority="default")
        record({"timestamp": now, "status": "warning", "http_code": status_code, "message": msg, "alerts": [str(status_code)]})
        return

    # All clear
    print("All clear.")
    record({"timestamp": now, "status": "clear", "http_code": status_code, "message": "No changes detected. All clear.", "alerts": []})


if __name__ == "__main__":
    check()
