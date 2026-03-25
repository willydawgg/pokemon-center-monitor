import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STATUS_FILE = "docs/status.json"
MAX_ALERTS = 100

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

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
                "Tags": "shopping,pokemon",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"ntfy failed: {e}")


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_smyths():
    url = "https://www.smythstoys.com/uk/en-gb/trading-cards/pokemon-cards/c/SM2301/"
    products = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".productListItem"):
            name_el = card.select_one(".productTitle")
            price_el = card.select_one(".productPrice, .price")
            link_el = card.select_one("a[href]")
            out_el = card.select_one(".outOfStock, .out-of-stock")

            name = name_el.get_text(strip=True) if name_el else None
            if not name:
                continue

            href = link_el["href"] if link_el else ""
            product_url = ("https://www.smythstoys.com" + href) if href.startswith("/") else href

            products.append({
                "name": name,
                "price": price_el.get_text(strip=True) if price_el else "",
                "url": product_url,
                "in_stock": out_el is None,
            })
    except Exception as e:
        print(f"Smyths error: {e}")
        return None
    return products


def scrape_argos():
    url = "https://www.argos.co.uk/search/pokemon-trading-cards/"
    products = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("[data-test='component-product-card'], [class*='ProductCard']"):
            name_el = card.select_one("[data-test='product-title'], h2, h3")
            price_el = card.select_one("[data-test='product-price'], [class*='Price']")
            link_el = card.select_one("a[href]")

            name = name_el.get_text(strip=True) if name_el else None
            if not name:
                continue

            href = link_el["href"] if link_el else ""
            product_url = ("https://www.argos.co.uk" + href) if href.startswith("/") else href

            card_text = card.get_text().lower()
            in_stock = "out of stock" not in card_text and "unavailable" not in card_text

            products.append({
                "name": name,
                "price": price_el.get_text(strip=True) if price_el else "",
                "url": product_url,
                "in_stock": in_stock,
            })
    except Exception as e:
        print(f"Argos error: {e}")
        return None
    return products


def scrape_asda():
    url = "https://www.asda.com/search?q=pokemon+trading+cards&department=toys"
    products = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".co-product, [class*='ProductCard'], [class*='product-card']"):
            name_el = card.select_one(".co-product__anchor, [class*='title'], h2, h3")
            price_el = card.select_one(".co-product__price, [class*='price']")
            link_el = card.select_one("a[href]")

            name = name_el.get_text(strip=True) if name_el else None
            if not name:
                continue

            href = link_el["href"] if link_el else ""
            product_url = ("https://www.asda.com" + href) if href.startswith("/") else href

            card_text = card.get_text().lower()
            in_stock = "out of stock" not in card_text and "unavailable" not in card_text

            products.append({
                "name": name,
                "price": price_el.get_text(strip=True) if price_el else "",
                "url": product_url,
                "in_stock": in_stock,
            })
    except Exception as e:
        print(f"Asda error: {e}")
        return None
    return products


def scrape_sportsdirect():
    url = "https://www.sportsdirect.com/search?term=pokemon+cards"
    products = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".productdiv, [class*='product-item']"):
            name_el = card.select_one(".productText, span[id*='ProductName'], h2, h3")
            price_el = card.select_one(".curPrice, [class*='price']")
            link_el = card.select_one("a[href]")

            name = name_el.get_text(strip=True) if name_el else None
            if not name:
                continue

            href = link_el["href"] if link_el else ""
            product_url = ("https://www.sportsdirect.com" + href) if href.startswith("/") else href

            card_text = card.get_text().lower()
            in_stock = "out of stock" not in card_text and "sold out" not in card_text

            products.append({
                "name": name,
                "price": price_el.get_text(strip=True) if price_el else "",
                "url": product_url,
                "in_stock": in_stock,
            })
    except Exception as e:
        print(f"Sports Direct error: {e}")
        return None
    return products


# ---------------------------------------------------------------------------
# Retailers registry
# ---------------------------------------------------------------------------

RETAILERS = {
    "smyths": {
        "name": "Smyths Toys",
        "scraper": scrape_smyths,
        "url": "https://www.smythstoys.com/uk/en-gb/trading-cards/pokemon-cards/c/SM2301/",
    },
    "argos": {
        "name": "Argos",
        "scraper": scrape_argos,
        "url": "https://www.argos.co.uk/search/pokemon-trading-cards/",
    },
    "asda": {
        "name": "Asda",
        "scraper": scrape_asda,
        "url": "https://www.asda.com/search?q=pokemon+trading+cards&department=toys",
    },
    "sportsdirect": {
        "name": "Sports Direct",
        "scraper": scrape_sportsdirect,
        "url": "https://www.sportsdirect.com/search?term=pokemon+cards",
    },
}


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"retailers": {}, "alerts": [], "last_updated": None}


def save_state(state):
    os.makedirs("docs", exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = load_state()

    for key, retailer in RETAILERS.items():
        print(f"\nChecking {retailer['name']}...")
        products = retailer["scraper"]()

        prev_map = {
            p["name"]: p
            for p in state.get("retailers", {}).get(key, {}).get("products", [])
        }

        if products is None:
            # Scrape failed — preserve last known products, mark error
            prev = state.get("retailers", {}).get(key, {})
            prev["status"] = "error"
            prev["last_checked"] = now
            state.setdefault("retailers", {})[key] = prev
            print(f"  Failed to scrape.")
            continue

        # Detect restocks / newly listed in-stock items
        for p in products:
            if not p["in_stock"]:
                continue
            prev = prev_map.get(p["name"])
            newly_in_stock = prev is None or not prev.get("in_stock", False)
            if newly_in_stock:
                event = "RESTOCK" if prev else "IN STOCK"
                body = p["name"]
                if p.get("price"):
                    body += f" — {p['price']}"
                body += f"\n{p['url'] or retailer['url']}"
                notify(f"Pokemon TCG {event} — {retailer['name']}", body)

                state.setdefault("alerts", []).insert(0, {
                    "timestamp": now,
                    "retailer": retailer["name"],
                    "retailer_key": key,
                    "product": p["name"],
                    "price": p.get("price", ""),
                    "url": p.get("url", retailer["url"]),
                    "type": "restock" if prev else "new",
                })

        state["alerts"] = state.get("alerts", [])[:MAX_ALERTS]

        in_stock = [p for p in products if p["in_stock"]]
        print(f"  {len(in_stock)}/{len(products)} in stock")

        state.setdefault("retailers", {})[key] = {
            "name": retailer["name"],
            "url": retailer["url"],
            "last_checked": now,
            "status": "ok",
            "products": products,
        }

    state["last_updated"] = now
    save_state(state)
    print("\nAll done.")


if __name__ == "__main__":
    run()
