#!/usr/bin/env python3
"""
Pokemon Center Queue Monitor — GitHub Actions edition
Checks pokemoncenter.com for virtual queue / waiting room activation
and sends a push notification to your phone via ntfy.sh when detected.
"""

import os
import sys
import requests
from datetime import datetime, timezone

# ── Configuration ──────────────────────────────────────────────────────────────

TARGET_URL  = "https://www.pokemoncenter.com/"
NTFY_TOPIC  = os.environ.get("NTFY_TOPIC", "")        # set as GitHub secret
NTFY_SERVER = "https://ntfy.sh"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Strings that appear in queue / virtual waiting-room systems
QUEUE_CONTENT_SIGNALS = [
    "queue-it.net",
    "queueit",
    "QueueIT",
    "waitingroom",
    "waiting-room",
    "virtual-queue",
    "virtualqueue",
    "crowdhandler",
    "crowd-handler",
    "inqueue",
]

QUEUE_COOKIE_SIGNALS = [
    "queueit",
    "queue-it",
    "QueueIT",
    "waiting",
    "crowdhandler",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def log(message: str, level: str = "INFO"):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now}] [{level}] {message}", flush=True)


def send_ntfy_alert(reasons: list[str]):
    """Send a push notification to the phone via ntfy.sh."""
    if not NTFY_TOPIC:
        log("NTFY_TOPIC secret not set — skipping push notification.", "WARN")
        return

    body = "Virtual queue detected on Pokemon Center!\n\n" + "\n".join(
        f"• {r}" for r in reasons[:5]
    )

    try:
        response = requests.post(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            data=body.encode("utf-8"),
            headers={
                "Title": "Pokemon Center DROP ALERT",
                "Priority": "urgent",
                "Tags": "rotating_light,pokemon",
            },
            timeout=10,
        )
        if response.ok:
            log("Push notification sent successfully.")
        else:
            log(f"ntfy.sh returned {response.status_code}: {response.text}", "WARN")
    except requests.RequestException as e:
        log(f"Failed to send push notification: {e}", "WARN")

# ── Queue Detection ────────────────────────────────────────────────────────────

def check_for_queue(session: requests.Session) -> tuple[bool, list[str]]:
    """
    Returns (queue_detected: bool, reasons: list[str]).
    Inspects redirects, cookies, headers, and page content.
    """
    reasons: list[str] = []

    try:
        response = session.get(
            TARGET_URL,
            headers=REQUEST_HEADERS,
            timeout=20,
            allow_redirects=True,
        )
    except requests.exceptions.Timeout:
        log("Request timed out — site may be under heavy load.", "WARN")
        return False, []
    except requests.exceptions.RequestException as e:
        log(f"Request error: {e}", "WARN")
        return False, []

    log(f"Response: HTTP {response.status_code} | Final URL: {response.url}")

    # 1. Redirect chain
    for redirect in response.history:
        location = redirect.headers.get("Location", "")
        if any(s.lower() in location.lower() for s in QUEUE_CONTENT_SIGNALS):
            reasons.append(f"Redirect to queue URL: {location}")

    # 2. Final URL
    if any(s.lower() in response.url.lower() for s in QUEUE_CONTENT_SIGNALS):
        reasons.append(f"Landed on queue URL: {response.url}")

    # 3. Cookies
    for cookie in session.cookies:
        if any(s.lower() in cookie.name.lower() for s in QUEUE_COOKIE_SIGNALS):
            reasons.append(f"Queue cookie set: {cookie.name}={cookie.value[:40]}")

    # 4. Response headers
    for name, value in response.headers.items():
        if any(s.lower() in value.lower() for s in QUEUE_CONTENT_SIGNALS):
            reasons.append(f"Queue signal in header '{name}': {value[:80]}")

    # 5. Page content
    content = response.text
    content_lower = content.lower()
    for signal in QUEUE_CONTENT_SIGNALS:
        if signal.lower() in content_lower:
            idx = content_lower.find(signal.lower())
            snippet = content[max(0, idx - 40): idx + len(signal) + 40].replace("\n", " ").strip()
            reasons.append(f"Signal '{signal}' found in page: ...{snippet}...")
            break  # one body hit is enough to flag

    return len(reasons) > 0, reasons

# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    log("=" * 55)
    log("Pokemon Center Queue Monitor — single check run")
    log(f"Target : {TARGET_URL}")
    log(f"ntfy   : {NTFY_SERVER}/{NTFY_TOPIC or '(topic not set)'}")
    log("=" * 55)

    session = requests.Session()
    detected, reasons = check_for_queue(session)

    if detected:
        log(f"QUEUE DETECTED — {len(reasons)} signal(s) found:", "ALERT")
        for r in reasons:
            log(f"  • {r}", "ALERT")
        send_ntfy_alert(reasons)
        # Exit with code 0 so GitHub Actions marks the run as success
        sys.exit(0)
    else:
        log("No queue detected. All clear.")
        sys.exit(0)


if __name__ == "__main__":
    main()
