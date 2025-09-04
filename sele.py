# selenium_branches_paged.py
import time, json, csv, re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://app.anousith.express/branches"

def setup_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--user-agent=Mozilla/5.0")
    return webdriver.Chrome(options=opts)

def wait_for_cards(driver, timeout=20):
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.row div.col-lg-6 div.card")))

def scroll_to_bottom(driver, pause=0.6, rounds=3):
    """Quick scroll to trigger any lazy content on this page."""
    last = 0
    for _ in range(rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new = driver.execute_script("return document.body.scrollHeight")
        if new == last:
            break
        last = new

def txt(el):
    try:
        return el.text.strip()
    except Exception:
        return None

num_re = re.compile(r"\s*([\d,\.]+)")

def leading_number(s):
    if not s:
        return None
    m = num_re.match(s)
    return m.group(1) if m else None

def scrape_one_page(driver):
    """Return list of dicts for the current page."""
    wait_for_cards(driver)
    scroll_to_bottom(driver)

    cards = driver.find_elements(By.CSS_SELECTOR, "div.row div.col-lg-6 div.card")
    out = []

    for card in cards:
        # Name
        name = None
        try:
            name = txt(card.find_element(By.CSS_SELECTOR, "b.textCustomBranch"))
        except Exception:
            pass

        # Phone (inside the border-top dashed row)
        phone = None
        try:
            phone_section = card.find_element(By.CSS_SELECTOR, "div[style*='border-top']")
            phone_b = phone_section.find_elements(By.CSS_SELECTOR, "b.textCustomBranch")
            if phone_b:
                phone = txt(phone_b[0])
        except Exception:
            pass

        # Status
        status = None
        try:
            status = txt(card.find_element(By.CSS_SELECTOR, "small.text-success"))
        except Exception:
            pass

        # Rating or count (leftmost number before ★ in right box)
        rating_or_count = None
        try:
            right_box = card.find_element(By.CSS_SELECTOR, "div[style*='justify-content: space-between'] > div")
            rating_or_count = leading_number(txt(right_box))
        except Exception:
            pass

        out.append({
            "name": name,
            "phone": phone,
            "status": status,
            "rating_or_count": rating_or_count,
            "page_url": driver.current_url
        })
    return out

def find_and_click_next(driver):
    """
    Try multiple 'Next' selectors. Returns True if it navigated, False if no next page.
    Adjust selectors to your pagination UI if needed.
    """
    candidates = [
        # Common patterns
        ("a[rel='next']", "css"),
        ("button[aria-label*='Next']", "css"),
        ("button[aria-label*='next']", "css"),
        ("a:has(.next)", "css"),                      # Selenium supports :has() now
        (".pagination .next a", "css"),
        (".pagination button.next", "css"),
        ("//a[contains(., 'Next') or contains(., 'next') or contains(., '›') or contains(., '»')]", "xpath"),
        ("//button[contains(., 'Next') or contains(., 'next') or contains(., '›') or contains(., '»')]", "xpath"),
    ]

    for selector, kind in candidates:
        try:
            if kind == "css":
                btns = driver.find_elements(By.CSS_SELECTOR, selector)
            else:
                btns = driver.find_elements(By.XPATH, selector)
            btns = [b for b in btns if b.is_displayed() and b.is_enabled()]
            if not btns:
                continue

            # Some sites disable the "Next" button at last page; skip disabled
            next_btn = btns[0]
            # Optional: check 'disabled' attribute/class
            disabled = (next_btn.get_attribute("disabled") in ("true", "disabled")) or \
                       ("disabled" in (next_btn.get_attribute("class") or "").lower())
            if disabled:
                continue

            # Click and wait for navigation
            current_url = driver.current_url
            next_btn.click()
            WebDriverWait(driver, 20).until(EC.staleness_of(next_btn))  # old DOM is stale after nav
            # wait page load
            WebDriverWait(driver, 20).until(EC.url_changes(current_url))
            time.sleep(0.8)  # small settle time
            return True
        except Exception:
            # try next strategy
            continue

    return False

def paginate_and_scrape(start_url=BASE_URL, max_pages=50, headless=False):
    driver = setup_driver(headless=headless)
    all_rows = []
    seen_keys = set()

    try:
        driver.get(start_url)
        for page_idx in range(1, max_pages + 1):
            rows = scrape_one_page(driver)

            # de-duplicate by (name, phone) pair
            for r in rows:
                key = (r.get("name"), r.get("phone"))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_rows.append(r)

            print(f"Page {page_idx}: got {len(rows)} rows; total unique {len(all_rows)}")

            # try to go next; if not found, stop
            if not find_and_click_next(driver):
                break
    finally:
        driver.quit()

    return all_rows

def save_outputs(rows, out_json="branches_all.json", out_csv="branches_all.csv"):
    Path(out_json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    keys = ["name", "phone", "status", "rating_or_count", "page_url"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    data = paginate_and_scrape(headless=False)   # set True for headless runs
    print(f"\nTotal unique branches: {len(data)}")
    save_outputs(data)
    print("Saved: branches_all.json & branches_all.csv")
