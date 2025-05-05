import csv
import time
import requests
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --------- 설정 ---------
SEOUL_SW = (37.413294, 126.734086)
SEOUL_NE = (37.715133, 127.269311)
STEP = 5

# --------- 드라이버 초기화 ---------
def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")  # 기존 방식
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ko-KR")
    options.add_argument("user-agent=Mozilla/5.0")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --------- 스크롤 ---------
def scroll_to_bottom(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# --------- 그리드 생성 ---------
def generate_grid_coords(sw_lat, sw_lng, ne_lat, ne_lng, steps):
    lat_range = [sw_lat + i * (ne_lat - sw_lat) / steps for i in range(steps)]
    lng_range = [sw_lng + i * (ne_lng - sw_lng) / steps for i in range(steps)]
    grid = []
    for i in range(len(lat_range) - 1):
        for j in range(len(lng_range) - 1):
            grid.append({
                'sw_lat': lat_range[i],
                'sw_lng': lng_range[j],
                'ne_lat': lat_range[i + 1],
                'ne_lng': lng_range[j + 1]
            })
    return grid

def generate_airbnb_url(sw_lat, sw_lng, ne_lat, ne_lng):
    return (
        f"https://www.airbnb.co.kr/s/서울/homes"
        f"?search_by_map=true&sw_lat={sw_lat}&sw_lng={sw_lng}"
        f"&ne_lat={ne_lat}&ne_lng={ne_lng}&zoom=14"
    )

# --------- CSV 저장 ---------
def save_to_csv(data_list, filename="airbnb_seoul_data.csv"):
    keys = ["link", "image", "rating", "review_count", "room_id"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for data in data_list:
            writer.writerow(data)

# --------- 유효 이미지 판단 ---------
def is_valid_image_url(url):
    if not url or url == "이미지 없음":
        return False
    blocked_keywords = ["user/", "profile", "airbnb-platform-assets", "photo_enhancement"]
    if any(keyword in url for keyword in blocked_keywords):
        return False
    if url.endswith(".png"):
        return False
    return True

# --------- 이미지 저장 ---------
def download_images(data_list, folder="images"):
    os.makedirs(folder, exist_ok=True)
    count = 0
    for i, item in enumerate(data_list, 1):
        url = item["image"]
        room_id = item["room_id"]
        if not is_valid_image_url(url):
            continue
        try:
            ext = url.split(".")[-1].split("?")[0]
            filename = f"{room_id}.{ext}"
            filepath = os.path.join(folder, filename)
            if not os.path.exists(filepath):
                img_data = requests.get(url, timeout=10).content
                with open(filepath, "wb") as f:
                    f.write(img_data)
                count += 1
                print(f"[{count}] ✅ 저장됨: {filename}")
            else:
                print(f"⚠️ 이미 존재함: {filename}")
        except Exception as e:
            print(f"❌ 이미지 다운로드 실패 ({url}): {e}")
    print(f"\n📷 총 {count}개의 이미지 저장 완료!")

# --------- 숙소 정보 수집 ---------
def get_all_listings(driver, seen_ids, result):
    time.sleep(5)
    scroll_to_bottom(driver)
    cards = driver.find_elements(By.XPATH, '//div[@role="group"]')
    listings = []
    for card in cards:
        try:
            link = card.find_element(By.XPATH, './/a[starts-with(@href, "/rooms/")]').get_attribute("href")
            if not link:
                continue
            room_id = link.split("/rooms/")[-1].split("?")[0]
            if room_id in seen_ids:
                continue
            seen_ids.add(room_id)
            try:
                images = card.find_elements(By.XPATH, ".//img")
                img_url = images[0].get_attribute("src") if images else "이미지 없음"
            except:
                img_url = "이미지 없음"
            try:
                spans = card.find_elements(By.TAG_NAME, "span")
                rating_text = next((s.text.strip() for s in spans if "평점" in s.text or "후기" in s.text or "★" in s.text), "평점 없음")
            except:
                rating_text = "평점 없음"
            rating_value = ""
            review_count = ""
            if "점" in rating_text:
                match = re.search(r"([0-9.]+)점", rating_text)
                if match:
                    rating_value = match.group(1)
                match = re.search(r"후기\s*([0-9]+)개", rating_text)
                if match:
                    review_count = match.group(1)
            elif "★" in rating_text:
                rating_value = rating_text
            listing = {
                "link": link,
                "image": img_url,
                "rating": rating_value,
                "review_count": review_count,
                "room_id": room_id
            }
            result.append(listing)
            listings.append(listing)
        except:
            continue
    return listings

# --------- 페이지 순회 ---------
def crawl_all_pages(driver, seen_ids, result):
    prev_first_link = None
    while True:
        listings = get_all_listings(driver, seen_ids, result)
        if not listings:
            print("⚠️ 숙소 없음 또는 로딩 실패, 중단")
            break
        first_link = listings[0]['link'] if listings else None
        if first_link == prev_first_link:
            print("⛔ 페이지 중복 감지됨, 루프 종료")
            break
        prev_first_link = first_link
        try:
            next_btn = driver.find_element(By.XPATH, '//a[@aria-label="다음"]')
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(3)
        except:
            break

# --------- 메인 ---------
def main():
    start_time = time.time()
    driver = init_driver(headless=False)
    grid = generate_grid_coords(*SEOUL_SW, *SEOUL_NE, STEP)
    urls = [generate_airbnb_url(**coords) for coords in grid]
    seen_ids = set()
    result = []
    for idx, url in enumerate(urls, 1):
        print(f"\n📍 그리드 {idx}/{len(urls)}: {url}")
        driver.get(url)
        crawl_all_pages(driver, seen_ids, result)
        print(f"➡️ 누적 숙소 수: {len(result)}개")
    save_to_csv(result)
    download_images(result)
    driver.quit()
    end_time = time.time()
    print(f"\n✅ 총 {len(result)}개의 숙소 정보를 airbnb_seoul_data.csv 에 저장 완료!")
    print(f"⏱️ 총 소요 시간: {end_time - start_time:.2f}초")

if __name__ == "__main__":
    main()
