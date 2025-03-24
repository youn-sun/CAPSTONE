import time
import os
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from io import BytesIO

# 웹드라이버 실행
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# 크롤링할 URL 설정
url = "https://www.airbnb.co.kr/s/%EC%84%9C%EC%9A%B8/homes?refinement_paths%5B%5D=%2Fhomes"

# Airbnb 사이트 열기
driver.get(url)

# 페이지 로딩 대기
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'c4mnd7m')]")))

print("✅ Airbnb 페이지가 성공적으로 열렸습니다.")

# 이미지 저장 폴더 생성
img_folder = "airbnb_images"
os.makedirs(img_folder, exist_ok=True)

# 데이터 저장 리스트
data_list = []
img_index = 1  

# 함수: 숙소 데이터를 가져오는 부분
def get_data_from_page():
    global data_list, img_index
    for i in range(1, 19):  # 상위 18개 숙소 확인
        try:
            xpath = f"(//div[contains(@class, 'c4mnd7m')])[{i}]//a"
            link_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            link = link_element.get_attribute("href")
            print(f"🔹 {img_index}. 숙소 링크: {link}")
            
            # 이미지 URL을 가져오는 함수
            def fetch_image_url():
                driver.execute_script(f"window.open('{link}', '_blank');")
                time.sleep(2)
                all_windows = driver.window_handles
                driver.switch_to.window(all_windows[-1])  
                
                try:
                    img_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//picture//img"))
                    )
                    img_url = img_element.get_attribute("src")
                    return img_url
                except:
                    return None
            
            # 이미지 URL 비동기적으로 가져오기
            img_url = fetch_image_url()
            
            if img_url:
                print(f"   🖼️ 첫 번째 이미지 URL: {img_url}")
                # 이미지 다운로드 및 저장
                response = requests.get(img_url)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    img_path = os.path.join(img_folder, f"숙소_{img_index}.jpg")
                    img.save(img_path)
                    print(f"   ✅ 이미지 저장 완료: {img_path}")
                else:
                    print(f"   ❌ 이미지 다운로드 실패")

            rating = None
            try:
                rating = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='r1lutz1s atm_c8_o7aogt atm_c8_l52nlx__oggzyc dir dir-ltr']"))
                ).text.strip()
                rating = ''.join([c for c in rating if c.isdigit() or c == '.'])
                rating = float(rating) if rating else None
            except Exception as e:
                print(f"   ❌ 평점 추출 실패: {e}")
            
            # 데이터 저장
            data_list.append({
                "숙소 링크": link,
                "평점": rating,
                "이미지 파일": img_path if img_url else "N/A"
            })

            driver.close()  # 새 탭 닫기
            driver.switch_to.window(driver.window_handles[0])  # 원래 탭으로 돌아가기

            img_index += 1  

        except Exception as e:
            print(f"❌ {i}. 정보를 가져오는 데 실패했습니다: {e}")

# 크롤링을 시작하는 함수
def crawl_pages(start_page, end_page):
    global data_list, img_index
    for page in range(start_page, end_page + 1):
        print(f"\n🔹 {page} 페이지 크롤링 시작!")
        if page > 1:
            next_page_button = driver.find_element(By.XPATH, f'//*[@id="site-content"]/div/div[3]/div/div/div/nav/div/a[{page}]')
            next_page_button.click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'c4mnd7m')]")))
        
        get_data_from_page()

    # 데이터 저장 (CSV 파일)
    df = pd.DataFrame(data_list)
    csv_path = "airbnb_data.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ 데이터 저장 완료: {csv_path}")

# 크롤링 시작
if __name__ == "__main__":
    start_page = 1
    end_page = 30  # 원하는 페이지 범위로 설정
    crawl_pages(start_page, end_page)
    driver.quit()
