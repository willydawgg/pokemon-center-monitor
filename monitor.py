import os
import requests

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
TARGET_URL = "https://www.pokemoncenter.com/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Queue-It signals — presence of any of these means a virtual queue is active
QUEUE_SIGNALS = [
    "queue-it.net",
    "queueit",
    "youarenext",
    "queueid",
    "waitingroom",
    "waiting room",
]

# Cloudflare/bot-protection challenge signals — these indicate the site has
# raised its security level beyond normal (challenge/under-attack mode)
SECURITY_SIGNALS = [
    "cf-browser-verification",
    "checking your browser",
    "ddos protection by cloudflare",
    "enable javascript and cookies",
    "cf_chl_opt",
    "datadome",
    "_pxcaptcha",
    "perimeterx",
    "access denied",
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


def check():
    try:
        resp = requests.get(TARGET_URL, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as e:
        notify(
            "Pokemon Center - Unreachable",
            f"Could not connect: {e}",
            priority="default",
        )
        return

    status = resp.status_code
    body = resp.text.lower()
    final_url = resp.url

    print(f"Status: {status}  |  Final URL: {final_url}")

    # 1. Queue-It redirect (URL-level)
    if "queue-it.net" in final_url or "queueit" in final_url.lower():
        notify(
            "QUEUE ACTIVE - Pokemon Center",
            f"Queue-It redirect detected. Get in line NOW!\n{TARGET_URL}",
            priority="urgent",
        )
        return

    # 2. Queue-It in page body
    hits = [s for s in QUEUE_SIGNALS if s in body]
    if hits:
        notify(
            "QUEUE ACTIVE - Pokemon Center",
            f"Virtual queue detected ({', '.join(hits)}). Head to the site!\n{TARGET_URL}",
            priority="urgent",
        )
        return

    # 3. Security/bot-protection challenge page
    sec_hits = [s for s in SECURITY_SIGNALS if s in body]
    if sec_hits:
        notify(
            "Security Change - Pokemon Center",
            f"Bot-protection challenge active ({', '.join(sec_hits)}). "
            f"Drop may be imminent.\n{TARGET_URL}",
            priority="high",
        )
        return

    # 4. 503 often precedes a drop (site going into queue mode)
    if status == 503:
        notify(
            "503 - Pokemon Center",
            f"Site returned 503 - may be ramping up for a drop.\n{TARGET_URL}",
            priority="high",
        )
        return

    # 5. Any other unexpected status
    if status not in (200, 301, 302, 304):
        notify(
            f"Unexpected Status {status} - Pokemon Center",
            f"HTTP {status} received. Worth checking.\n{TARGET_URL}",
            priority="default",
        )
        return

    print("No queue or security changes detected. All clear.")


if __name__ == "__main__":
    check()
