import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ──────────────────────────────────────────────
# CONFIG — edit these
# ──────────────────────────────────────────────
EMAIL_SENDER   = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"   # Gmail App Password (not your real password)
EMAIL_RECEIVER = "your_email@gmail.com"
DATA_FILE      = "tracked_products.json"
CHECK_INTERVAL = 60 * 60  # check every 1 hour (in seconds)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ──────────────────────────────────────────────
# DATA STORAGE
# ──────────────────────────────────────────────

def load_products():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_products(products):
    with open(DATA_FILE, "w") as f:
        json.dump(products, f, indent=2)

# ──────────────────────────────────────────────
# PRICE SCRAPER
# ──────────────────────────────────────────────

def get_price(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # ── Amazon ──
        if "amazon" in url:
            price_whole = soup.find("span", {"class": "a-price-whole"})
            price_fraction = soup.find("span", {"class": "a-price-fraction"})
            title = soup.find("span", {"id": "productTitle"})
            if price_whole:
                price_str = price_whole.text.strip().replace(",", "").replace(".", "")
                fraction = price_fraction.text.strip() if price_fraction else "00"
                price = float(f"{price_str}.{fraction}")
                name = title.text.strip() if title else "Amazon Product"
                return price, name

        # ── Daraz ──
        elif "daraz" in url:
            price_tag = soup.find("span", {"class": "pdp-price"})
            title = soup.find("h1", {"class": "pdp-mod-product-badge-title"})
            if price_tag:
                price_str = price_tag.text.strip().replace(",", "").replace("৳", "").replace("Rs.", "").strip()
                price = float("".join(filter(lambda x: x.isdigit() or x == ".", price_str)))
                name = title.text.strip() if title else "Daraz Product"
                return price, name

        # ── Generic fallback — looks for common price patterns ──
        for selector in [
            {"itemprop": "price"},
            {"class": "price"},
            {"class": "product-price"},
            {"class": "sale-price"},
        ]:
            tag = soup.find(attrs=selector)
            if tag:
                text = tag.get("content") or tag.text
                price_str = "".join(filter(lambda x: x.isdigit() or x == ".", text.strip()))
                if price_str:
                    title = soup.find("h1")
                    name = title.text.strip() if title else url
                    return float(price_str), name

        return None, None

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return None, None

# ──────────────────────────────────────────────
# EMAIL ALERT
# ──────────────────────────────────────────────

def send_email(product_name, url, old_price, new_price, target_price):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 Price Drop Alert: {product_name}"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = EMAIL_RECEIVER

        body = f"""
        <h2>💰 Price Drop Detected!</h2>
        <p><b>Product:</b> {product_name}</p>
        <p><b>Old Price:</b> {old_price}</p>
        <p><b>New Price:</b> <span style="color:green"><b>{new_price}</b></span></p>
        <p><b>Your Target:</b> {target_price}</p>
        <p><a href="{url}">👉 Buy Now</a></p>
        <p><small>Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
        """

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

        print(f"✅ Email sent for: {product_name}")

    except Exception as e:
        print(f"❌ Email error: {e}")

# ──────────────────────────────────────────────
# MENU
# ──────────────────────────────────────────────

def add_product():
    print("\n── Add Product ──")
    url = input("Product URL: ").strip()
    print("⏳ Fetching current price...")
    price, name = get_price(url)

    if price is None:
        print("❌ Could not fetch price. Check the URL.")
        return

    print(f"✅ Found: {name}")
    print(f"   Current Price: {price}")

    target = input("Set target price (alert when price drops to this): ").strip()
    try:
        target_price = float(target)
    except ValueError:
        print("❌ Invalid price.")
        return

    products = load_products()
    products.append({
        "url": url,
        "name": name,
        "target_price": target_price,
        "last_price": price,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history": [{"price": price, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]
    })
    save_products(products)
    print(f"✅ Now tracking: {name}")

def list_products():
    products = load_products()
    if not products:
        print("\n📭 No products tracked yet.")
        return
    print("\n── Tracked Products ──")
    for i, p in enumerate(products):
        print(f"\n[{i+1}] {p['name']}")
        print(f"     Current : {p['last_price']}")
        print(f"     Target  : {p['target_price']}")
        print(f"     Added   : {p['added_at']}")

def remove_product():
    products = load_products()
    if not products:
        print("📭 No products to remove.")
        return
    list_products()
    idx = input("\nEnter number to remove: ").strip()
    try:
        i = int(idx) - 1
        removed = products.pop(i)
        save_products(products)
        print(f"✅ Removed: {removed['name']}")
    except (ValueError, IndexError):
        print("❌ Invalid selection.")

def check_prices_once():
    products = load_products()
    if not products:
        print("📭 No products tracked.")
        return

    print(f"\n⏳ Checking {len(products)} product(s)...")
    updated = False

    for p in products:
        price, _ = get_price(p["url"])
        if price is None:
            print(f"❌ Could not fetch: {p['name']}")
            continue

        old_price = p["last_price"]
        print(f"\n📦 {p['name']}")
        print(f"   Old: {old_price} → New: {price}")

        p["history"].append({
            "price": price,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        p["last_price"] = price
        updated = True

        if price <= p["target_price"]:
            print(f"   🎉 TARGET REACHED! Sending email...")
            send_email(p["name"], p["url"], old_price, price, p["target_price"])
        elif price < old_price:
            print(f"   📉 Price dropped but not at target yet.")
        else:
            print(f"   📈 No drop yet.")

    if updated:
        save_products(products)

def start_auto_tracking():
    print(f"\n🚀 Auto tracking started (every {CHECK_INTERVAL // 60} min). Press Ctrl+C to stop.\n")
    while True:
        check_prices_once()
        print(f"\n⏰ Next check in {CHECK_INTERVAL // 60} minutes...")
        time.sleep(CHECK_INTERVAL)

def show_history():
    products = load_products()
    if not products:
        print("📭 No products tracked.")
        return
    list_products()
    idx = input("\nEnter number to view history: ").strip()
    try:
        i = int(idx) - 1
        p = products[i]
        print(f"\n── Price History: {p['name']} ──")
        for h in p["history"]:
            print(f"   {h['date']}  →  {h['price']}")
    except (ValueError, IndexError):
        print("❌ Invalid selection.")

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    print("=" * 45)
    print("       🛒 Price Tracker")
    print("=" * 45)

    while True:
        print("\n1. Add product")
        print("2. List tracked products")
        print("3. Check prices now")
        print("4. View price history")
        print("5. Remove product")
        print("6. Start auto tracking")
        print("0. Exit")

        choice = input("\nChoose: ").strip()

        if   choice == "1": add_product()
        elif choice == "2": list_products()
        elif choice == "3": check_prices_once()
        elif choice == "4": show_history()
        elif choice == "5": remove_product()
        elif choice == "6": start_auto_tracking()
        elif choice == "0": print("👋 Bye!"); break
        else: print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
