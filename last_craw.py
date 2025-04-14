import time
import os
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO

def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
        # 추가 옵션: 리소스 제한, GPU 사용 비활성화 등 (필요에 따라)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_data_from_page(driver, img_folder, data_list, current_img_index):

    for i in range(1, 19):
        try:
            xpath = f"(//div[contains(@class, 'c4mnd7m')])[{i}]//a"
            link_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            link = link_element.get_attribute("href")
            print(f"🔹 {current_img_index}. 숙소 링크: {link}")

            # 상세 정보 페이지를 새 탭에서 열기
            driver.execute_script(f"window.open('{link}', '_blank');")
            time.sleep(3)
            all_windows = driver.window_handles
            driver.switch_to.window(all_windows[-1])  # 새 탭으로 전환

            # 첫 번째 이미지 URL 추출 및 저장
            img_url = None
            try:
                img_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//picture//img"))
                )
                img_url = img_element.get_attribute("src")
                if img_url:
                    print(f"   🖼️ 첫 번째 이미지 URL: {img_url}")
                    response = requests.get(img_url)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        img_path = os.path.join(img_folder, f"숙소_{current_img_index}.jpg")
                        img.save(img_path)
                        print(f"   ✅ 이미지 저장 완료: {img_path}")
                    else:
                        print("   ❌ 이미지 다운로드 실패")
                        img_path = "N/A"
                else:
                    print("   ❌ 이미지 URL을 찾을 수 없습니다.")
                    img_path = "N/A"
            except Exception as e:
                print(f"   ❌ 첫 번째 이미지를 가져오는 데 실패했습니다: {e}")
                img_path = "N/A"

            # 숙소 평점 추출 (두 XPath를 순차적으로 사용)
            rating = None
            try:
                rating = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((
                        By.XPATH, "//*[@id='site-content']/div/div[1]/div[3]/div/div[1]/div/div[1]/div/div/div/section/div[3]/div[2]"
                    ))
                ).text.strip()
                rating = ''.join([c for c in rating if c.isdigit() or c == '.'])
                rating = float(rating) if rating else None
            except Exception as e:
                print(f"   ❌ 기존 XPath로 평점 추출 실패: {e}")
                try:
                    rating = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((
                            By.XPATH, "//*[@id='site-content']/div/div[1]/div[3]/div/div[1]/div/div[2]/div/div/div/a/div/div[6]/div[1]"
                        ))
                    ).text.strip()
                    rating = ''.join([c for c in rating if c.isdigit() or c == '.'])
                    rating = float(rating) if rating else None
                except Exception as e2:
                    print(f"   ❌ 새로운 XPath로 평점 추출 실패: {e2}")
                    rating = None
            if rating is not None:
                print(f"   ⭐ 숙소 평점: {rating}")
            else:
                print("   ❌ 숙소 평점을 찾을 수 없습니다.")

            # 후기 개수 추출 (두 XPath를 순차적으로 사용)
            review_count = None
            try:
                review_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((
                        By.XPATH, "//*[@id='site-content']/div/div[1]/div[3]/div/div[1]/div/div[1]/div/div/div/section/div[3]/a"
                    ))
                )
                review_text = review_element.text.strip()
                review_count = ''.join([c for c in review_text if c.isdigit()])
                review_count = int(review_count) if review_count else None
            except Exception as e:
                print(f"   ❌ 후기 추출 실패 (첫 번째 XPath): {e}")
                try:
                    review_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((
                            By.XPATH, "//*[@id='site-content']/div/div[1]/div[3]/div/div[1]/div/div[2]/div/div/div/a/div/div[10]/div[1]"
                        ))
                    )
                    review_text = review_element.text.strip()
                    review_count = ''.join([c for c in review_text if c.isdigit()])
                    review_count = int(review_count) if review_count else None
                except Exception as e2:
                    print(f"   ❌ 후기 추출 실패 (두 번째 XPath): {e2}")
                    review_count = None
            if review_count is not None:
                print(f"   💬 후기 개수: {review_count}")
            else:
                print("   ❌ 후기 개수를 찾을 수 없습니다.")

            data_list.append({
                "숙소 링크": link,
                "평점": rating,
                "후기 개수": review_count,
                "이미지 파일": img_path if img_url else "N/A"
            })

            driver.close()  # 상세 페이지 탭 닫기
            driver.switch_to.window(all_windows[0])  # 원래 탭으로 복귀
            current_img_index += 1

        except Exception as e:
            print(f"❌ {i}. 정보를 가져오는 데 실패했습니다: {e}")
    return data_list, current_img_index

def crawl_pages(driver, start_page, end_page, img_folder):
    global data_list, img_index
    base_url = "https://www.airbnb.co.kr"
    for page in range(start_page, end_page + 1):
        print(f"\n🔹 {page} 페이지 크롤링 시작!")
        # 첫 페이지 이후에는 '다음' 버튼의 href를 활용해 페이지 이동
        if page > start_page:
            next_page_xpath = "//*[@id='site-content']/div/div[3]/div/div/div/nav/div/a[5]"
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, next_page_xpath))
                )
                # href 속성 추출
                next_href = next_button.get_attribute("href")
                if not next_href:
                    print("❌ '다음' 버튼에 href 속성이 존재하지 않습니다.")
                    break
                # href가 상대 경로인 경우 base_url을 붙임.
                if next_href.startswith("/"):
                    next_href = base_url + next_href
                print("➡️ 다음 페이지 URL:", next_href)
                # 추출한 URL로 이동
                driver.get(next_href)
                time.sleep(5)
            except Exception as e:
                print(f"❌ 페이지 이동 실패: {e}")
                break
        data_list, img_index = get_data_from_page(driver, img_folder, data_list, img_index)
    return data_list

def main():
    # 설정 변수 (여기서 한 번에 설정)
    HEADLESS = True
    URL = "https://www.airbnb.co.kr/s/%EA%B0%95%EB%82%A8%EA%B5%AC-%C2%B7-%EA%B0%80%EB%A1%9C%EC%88%98%EA%B8%B8/homes?refinement_paths%5B%5D=%2Fhomes&checkin=2025-05-15&checkout=2025-05-16&date_picker_type=calendar&search_type=user_map_move&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-05-01&monthly_length=3&monthly_end_date=2025-08-01&price_filter_input_type=0&price_filter_num_nights=1&channel=EXPLORE&zoom_level=15.16526909546298&place_id=ChIJI_IUbOujfDUReyU3t6AyGoM&acp_id=t-g-ChIJI_IUbOujfDUReyU3t6AyGoM&source=structured_search_input_header&query=%EA%B0%95%EB%82%A8%EA%B5%AC%20%C2%B7%20%EA%B0%80%EB%A1%9C%EC%88%98%EA%B8%B8&parent_city_place_id=ChIJzWXFYYuifDUR64Pq5LTtioU&search_mode=regular_search&ne_lat=37.52181233047573&ne_lng=127.03910008096176&sw_lat=37.49895303346476&sw_lng=127.0153342367696&zoom=15.16526909546298&search_by_map=true"
    START_PAGE = 1
    END_PAGE = 13
    IMG_FOLDER = "airbnb_images_2"
    CSV_FILENAME = "airbnb_data_2.csv"

    # 이미지 폴더 생성
    os.makedirs(IMG_FOLDER, exist_ok=True)

    # 웹드라이버 초기화 (headless 모드)
    driver = init_driver(HEADLESS)
    driver.get(URL)
    time.sleep(5)
    print("✅ Airbnb 페이지가 성공적으로 열렸습니다.")

    global data_list, img_index
    data_list = []
    img_index = 1

    # 페이지별 크롤링 수행
    crawl_pages(driver, START_PAGE, END_PAGE, IMG_FOLDER)

    # 데이터 CSV 파일로 저장
    df = pd.DataFrame(data_list)
    df.to_csv(CSV_FILENAME, index=False, encoding="utf-8-sig")
    print(f"\n✅ 데이터 저장 완료: {CSV_FILENAME}")

    driver.quit()

if __name__ == "__main__":
    main()
