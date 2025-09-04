import csv
from anyio import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re, json, time

URL = "https://app.anousith.express/branches"

driver = webdriver.Chrome()
driver.get(URL)
def save_outputs(rows, out_json="branches_province.json", out_csv="branches_province.csv"):
    Path(out_json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    keys = ["name", "phone", "status", "rating_or_count", "page_url", "province"]

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
wait = WebDriverWait(driver, 30)

# 1. Wait until the React-Select input appears
search_box = wait.until(
    EC.presence_of_element_located((By.ID, "react-select-2-input"))
)
list_provinces = ["1. ນະຄອນຫຼວງວຽງຈັນ", "2. ແຂວງ ສະຫວັນນະເຂດ","3. ແຂວງ ຈຳປາສັກ", "4. ແຂວງ ບໍລິຄຳໄຊ",
                  "5. ແຂວງ ຄຳມ່ວນ", "6. ແຂວງ ສາລະວັນ", "7. ແຂວງ ເຊກອງ", "8. ແຂວງ ອັດຕະປື",
                  "9. ແຂວງ ຫຼວງພະບາງ", "10. ແຂວງ ຫຼວງນ້ຳທາ", "11. ແຂວງ ຫົວພັນ", "12. ແຂວງ ອຸດົມໄຊ",
                  "13. ແຂວງ ບໍ່ແກ້ວ", "14. ແຂວງ ວຽງຈັນ", "15. ແຂວງ ໄຊຍະບູລີ",
                  "16. ແຂວງ ຊຽງຂວາງ", "17. ແຂວງ ຜົ້ງສາລີ", "18. ແຂວງ ໄຊສົມບູນ",]

# 2. Type province/region into the dropdown
# province = "2. ແຂວງ ສະຫວັນນະເຂດ"
for province in list_provinces:
    search_box.send_keys(province)
    search_box.send_keys(Keys.ENTER)

# 3. Wait until cards are visible after filtering
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.row div.col-lg-6 div.card")))
    # 4. Scroll until no more new cards
    def scroll_until_done(driver, pause=1.0, max_rounds=20):
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(max_rounds):
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    scroll_until_done(driver)

    # 5. Scrape structured data
    branches_province = []

    cards = driver.find_elements(By.CSS_SELECTOR, "div.row div.col-lg-6 div.card")

    for card in cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, "b.textCustomBranch").text.strip()
        except:
            name = None

        try:
            phone_section = card.find_element(By.CSS_SELECTOR, "div[style*='border-top']")
            phone = phone_section.find_element(By.CSS_SELECTOR, "b.textCustomBranch").text.strip()
        except:
            phone = None
        try:
            status = card.find_element(By.CSS_SELECTOR, "small.text-success").text.strip()
        except:
            status = None

        try:
            status = card.find_element(By.CSS_SELECTOR, "small.text-success").text.strip()
        except:
            status = None

        rating_or_count = None

        try:
            right_box = card.find_element(By.CSS_SELECTOR, "div[style*='justify-content: space-between'] > div")
            txt = right_box.text.strip()
            m = re.match(r"([\d,\.]+)", txt)
            if m:
                rating_or_count = m.group(1)
        except:
            pass
        branches_province.append({
            "name": name,
            "phone": phone,
            "status": status,
            "rating_or_count": rating_or_count,
            "province": province.split(".")[1].strip()
        })

        # 6. Print result
        print(json.dumps(branches_province, ensure_ascii=False, indent=2))
        print(f"Total branches scraped: {len(branches_province)}")

    save_outputs(branches_province)

driver.quit()
