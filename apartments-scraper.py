from __future__ import annotations
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import List
from bs4 import BeautifulSoup 
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import gspread
from oauth2client.service_account import ServiceAccountCredentials


class Listing:
    link: str
    location: str
    price: str
    size: str | None
    in_unit_laundry: bool
    contact: str | None

    def to_row(self) -> List[str]:
        return [
            self.link,
            self.location,
            self.price,
            self.size or "–",
            "TRUE" if self.in_unit_laundry else "FALSE",
            self.contact or "–",
        ]

# Selenium helpers

def make_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    # if headless:
    #     opts.add_argument("--headless=new")
    opts.add_argument("--disable‑gpu")
    opts.add_argument("--window‑size=1920,1080")
    opts.add_argument("--no‑sandbox")
    opts.add_argument("--disable‑dev‑shm‑usage")
    driver = webdriver.Chrome(options=opts)
    return driver


def close_modal(driver: webdriver.Chrome):
    try:
        driver.find_element(By.CSS_SELECTOR, "button[data‑tracking='dialog_accept']").click()
    except NoSuchElementException:
        pass


# Parsing utilities

PRICE_RE = re.compile(r"\$([\d,]+)")
SIZE_RE = re.compile(r"(\d{3,4})\s*sq\.?\s*ft", re.I)


def min_price(price_text: str) -> int | None:
    if not price_text or "call" in price_text.lower():
        return None
    m = PRICE_RE.findall(price_text)
    return int(m[0].replace(",", "")) if m else None


# Scraping

SEARCH_URLS = {
    "City": "https://www.apartments.com/[city]/"
}

BEDROOM_ALLOWED = {0, 1, 2}  # 0 for studio
MAX_PRICE = {0: 1400, 1: 1400, 2: 2100}


def extract_listing_cards(html: str):
    soup = BeautifulSoup(html, "html.parser")
    return soup.select("article.placard")


def has_in_unit_laundry(soup: BeautifulSoup) -> bool:
    amenities = " ".join(span.get_text(" ") for span in soup.select("p.property-amenities span")).lower()
    return any(term in amenities for term in ("in‑unit washer", "in‑unit laundry", "washer/dryer – in unit"))


def parse_listing_page(driver: webdriver.Chrome, url: str) -> Listing | None:
    driver.get(url)
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    heading = soup.find("h1")
    location = heading.get_text(strip=True) if heading else "Unknown"

    # Price
    price_el = soup.select_one("span[itemprop='priceRange'], span[data‑t='unitRent']")
    price_text = price_el.get_text(" ", strip=True) if price_el else ''

    # Size (first occurrence of "sq ft")
    size_match = SIZE_RE.search(soup.get_text(" "))
    if size_match:
        size_val = size_match.group(1)
        size = f"{size_val} sq ft" if int(size_val) > 100 else None
    else:
        size = None

    # In‑unit laundry – scan amenities
    in_unit = has_in_unit_laundry(soup)

    # Contact – grab phone number if any
    phone_el = soup.select_one("button.phone-link span")
    contact = phone_el.get_text(strip=True) if phone_el else "N/A"

    return Listing(link=url, location=location, price=price_text, size=size, in_unit_laundry=in_unit, contact=contact)


def scrape_city(driver: webdriver.Chrome, city: str) -> List[Listing]:
    listings: List[Listing] = []
    url = SEARCH_URLS[city]
    driver.get(url)
    close_modal(driver)
    time.sleep(3)

    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    cards = extract_listing_cards(driver.page_source)
    print(f"{city}: found {len(cards)} cards on search page")

    for card in cards:
        # print("\n--- CARD HTML PREVIEW ---")
        # print(card.prettify())
        # break
        link_el = card.select_one("a.property-link")
        beds_el = card.select_one("p.property-beds")
        price_el = card.select_one("p.property-pricing")
        if not (link_el and price_el and beds_el):
            print(f"SKIPPING CARD — Missing fields | link: {bool(link_el)} | price: {bool(price_el)} | beds: {bool(beds_el)}")
            continue

        beds_text = beds_el.get_text(strip=True).lower()
        price_text = price_el.get_text(" ", strip=True)
        
        bed_count = 0 if "studio" in beds_text else None
        if bed_count is None:
            m = re.search(r"(\d)\s*bed", beds_text)
            bed_count = int(m.group(1)) if m else None

        if bed_count is None or bed_count not in MAX_PRICE:
            continue

        price_min = min_price(price_text)
        if price_min is None or price_min > MAX_PRICE[bed_count]:
            continue

        print(f"{city} | Beds: {beds_text} | Price: {price_text}")
        listing_url = link_el["href"].split("?", 1)[0]
        try:
            with make_driver() as detail_driver:
                listing = parse_listing_page(detail_driver, listing_url)
            price_val = min_price(listing.price or price_text)
            if listing and price_val is not None and price_val <= MAX_PRICE[bed_count]:
                listings.append(listing)
        except Exception as e:
            import traceback
            print(f"Error scraping {listing_url}: {type(e).__name__} – {e}")
            traceback.print_exc()

    return listings


# Google Sheets I/O

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def open_sheet(creds_json_path: str, spreadsheet_id: str, worksheet_name: str = "Sheet1") -> gspread.Worksheet:
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json_path, SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(spreadsheet_id)
    try:
        return sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=worksheet_name, rows="100", cols="20")


def write_to_google_sheet(ws: gspread.Worksheet, listings: List[Listing]):
    # Clear previous content except header
    ws.resize(rows=2)

    header = ["Link", "Location", "Price", "Size", "in‑unit laundry (T/F)", "Contact"]
    ws.update("A1:F1", [header])

    # Sort listings by numeric min price
    listings.sort(key=lambda l: min_price(l.price) or float('inf'))

    rows = [listing.to_row() for listing in listings]
    # Batch update to minimize API calls
    ws.append_rows(rows, value_input_option="USER_ENTERED")

    print(f"Wrote {len(rows)} listings to Google Sheets")

def main():
    if len(sys.argv) < 3:
        print("Usage: python apartments_scraper.py <google‑creds.json> <spreadsheet_id>")
        sys.exit(1)

    creds_json_path = sys.argv[1]
    spreadsheet_id = sys.argv[2]

    driver = make_driver()
    try:
        all_listings: List[Listing] = []
        for city in SEARCH_URLS:
            listings = scrape_city(driver, city)
            all_listings.extend(listings)

        ws = open_sheet(creds_json_path, spreadsheet_id)
        write_to_google_sheet(ws, all_listings)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
