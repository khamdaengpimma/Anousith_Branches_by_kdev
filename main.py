from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re, json, time
from pathlib import Path
from collections import defaultdict

URL = "https://app.anousith.express/branches"

LIST_PROVINCES = [
    "1. ນະຄອນຫຼວງວຽງຈັນ", "2. ແຂວງ ສະຫວັນນະເຂດ", "3. ແຂວງ ຈຳປາສັກ",
    "4. ແຂວງ ບໍລິຄຳໄຊ", "5. ແຂວງ ຄຳມ່ວນ", "6. ແຂວງ ສາລະວັນ",
    "7. ແຂວງ ເຊກອງ", "8. ແຂວງ ອັດຕະປື", "9. ແຂວງ ຫຼວງພະບາງ",
    "10. ແຂວງ ຫຼວງນ້ຳທາ", "11. ແຂວງ ຫົວພັນ", "12. ແຂວງ ອຸດົມໄຊ",
    "13. ແຂວງ ບໍ່ແກ້ວ", "14. ແຂວງ ວຽງຈັນ", "15. ແຂວງ ໄຊຍະບູລີ",
    "16. ແຂວງ ຊຽງຂວາງ", "17. ແຂວງ ຜົ້ງສາລີ", "18. ແຂວງ ໄຊສົມບູນ",
]

def wait_for_cards(wait):
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.row div.col-lg-6 div.card")))

def scroll_until_done(driver, pause=0.8, max_rounds=25):
    last_h = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            break
        last_h = new_h

def get_card_names(driver):
    return [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, "div.row div.col-lg-6 div.card b.textCustomBranch")]

def select_province(driver, wait, text):
    inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id^='react-select-'][id$='-input']")))
    inp.click()
    inp.send_keys(Keys.CONTROL, "a"); inp.send_keys(Keys.BACK_SPACE)
    time.sleep(0.15)
    inp.send_keys(text)
    listbox = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id^='react-select-'][id$='-listbox']")))
    try:
        option = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            f"//div[@id='{listbox.get_attribute('id')}']//div[@role='option'][contains(normalize-space(.), {json.dumps(text)})]"
        )))
        option.click()
    except Exception:
        inp.send_keys(Keys.ENTER)

def scrape_cards(driver):
    cards = driver.find_elements(By.CSS_SELECTOR, "div.row div.col-lg-6 div.card")
    out, num_re = [], re.compile(r"([\d,\.]+)")
    for card in cards:
        try:   name = card.find_element(By.CSS_SELECTOR, "b.textCustomBranch").text.strip()
        except: name = None
        try:
            phone_row = card.find_element(By.CSS_SELECTOR, "div[style*='border-top']")
            phone = phone_row.find_element(By.CSS_SELECTOR, "b.textCustomBranch").text.strip()
        except: phone = None
        try:   status = card.find_element(By.CSS_SELECTOR, "small.text-success").text.strip()
        except: status = None
        rating = None
        try:
            right_box = card.find_element(By.CSS_SELECTOR, "div[style*='justify-content: space-between'] > div")
            m = num_re.match(right_box.text.strip()); rating = m.group(1) if m else None
        except: pass
        out.append({"name": name, "phone": phone, "status": status, "rating_or_count": rating})
    return out

def sanitize_fname(s: str) -> str:
    # Keep unicode, remove forbidden filename chars on Windows/macOS
    return re.sub(r'[\\/:*?"<>|]', '_', s)

# ----------------- main -----------------
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 30)

all_rows = []
try:
    driver.get(URL)
    wait_for_cards(wait)

    for prov in LIST_PROVINCES:
        prev_names = get_card_names(driver)
        driver.execute_script("window.scrollTo(0, 0);"); time.sleep(0.2)

        select_province(driver, wait, prov)

        WebDriverWait(driver, 30).until(
            lambda d: (get_card_names(d) != prev_names) or len(get_card_names(d)) > 0
        )

        scroll_until_done(driver)

        seen = set()
        rows = []
        for r in scrape_cards(driver):
            key = (r.get("name"), r.get("phone"))
            if key in seen: 
                continue
            seen.add(key)
            r["province"] = prov.split(".")[1].strip()
            rows.append(r)

        print(f"{prov}: {len(rows)} branches")
        all_rows.extend(rows)

finally:
    driver.quit()

# -------- SAVE TO JSON --------
out_dir = Path("branches_output")
out_dir.mkdir(exist_ok=True)

# 1) All provinces in one file
all_file = out_dir / "branches_all.json"
all_file.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved ALL -> {all_file.resolve()}")

# 2) One file per province
by_province = defaultdict(list)
for row in all_rows:
    by_province[row["province"]].append(row)

for prov, rows in by_province.items():
    fname = out_dir / f"{sanitize_fname(prov)}.json"
    fname.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {prov} -> {fname.resolve()}")
