import csv
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def init_driver():
    """
    봇 탐지를 우회하기 위한 강력한 ChromeOptions 및 CDP 설정
    """
    options = webdriver.ChromeOptions()
    
    # 자동화 제어 플래그 및 감지 옵션 비활성화
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # 실제 브라우저 User-Agent 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # navigator.webdriver 속성 재정의를 통한 봇 감지 회피
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    return driver

def scroll_and_load_reviews(driver):
    """
    후기 영역까지 스크롤 및 탭 클릭으로 DOM 데이터 활성화
    """
    # 1. '후기' 탭 위치 탐색 및 클릭 시도
    try:
        tabs = driver.find_elements(By.XPATH, "//*[contains(text(), '후기')]")
        for tab in tabs:
            if tab.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", tab)
                time.sleep(1.5)
                break
    except Exception:
        pass

    # 2. 리뷰 요소가 화면에 그려질 때까지 점진적 스크롤 다운 (최대 10회)
    for _ in range(10):
        reviews = driver.find_elements(By.CSS_SELECTOR, "p[class*='e6cseyw1']")
        if len(reviews) > 0:
            return True
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(0.8)
        
    return False

def click_next_page(driver, next_page_num):
    """
    페이지 이동 (페이지 번호 직접 클릭 -> 다음 화살표 버튼 클릭 순차 시도)
    """
    # 1차: 다음 페이지 숫자 버튼 직접 클릭 (예: 2, 3, 4 ...)
    try:
        page_btns = driver.find_elements(By.XPATH, f"//button[text()='{next_page_num}']")
        for btn in page_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn)
                return True
    except Exception:
        pass

    # 2차: 첨부 이미지 기반 클래스('e8bfz7t3') 다음 버튼 클릭
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "button[class*='e8bfz7t3']")
        if next_btn.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", next_btn)
            return True
    except Exception:
        pass

    # 3차: 화살표 내부 div('e10g3xe20')를 포함하는 버튼 클릭
    try:
        next_btns = driver.find_elements(By.CSS_SELECTOR, "button[class*='css-']")
        for btn in next_btns:
            if btn.is_displayed() and btn.find_elements(By.CSS_SELECTOR, "div[class*='e10g3xe20']"):
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn)
                return True
    except Exception:
        pass

    return False

def crawl_kurly_reviews(target_url, max_pages=20):
    driver = init_driver()
    wait = WebDriverWait(driver, 10)
    
    filename = "kurly_reviews.csv"
    file = open(filename, "w", encoding="utf-8-sig", newline="")
    writer = csv.writer(file)
    writer.writerow(["상품명", "날짜", "리뷰"])
    
    try:
        driver.get(target_url)
        time.sleep(random.uniform(3.0, 4.0))
        
        # 페이지 대표 상품명 추출 (기본 데이터)
        try:
            main_title_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
            main_title = main_title_elem.text.strip()
        except Exception:
            main_title = "[사미헌] 갈비탕"

        for current_page in range(1, max_pages + 1):
            print(f"[{current_page}/{max_pages}] 페이지 수집 중...")
            
            # 후기 영역 스크롤 및 로딩 보장
            loaded = scroll_and_load_reviews(driver)
            if not loaded:
                print(f"  └ {current_page}페이지 리뷰 로딩 미완료. 추가 스크롤을 시도합니다.")
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(2.0)

            # 요소 수집 (제시해주신 HTML 이미지의 식별 클래스 적용)
            review_elems = driver.find_elements(By.CSS_SELECTOR, "p[class*='e6cseyw1']")
            product_elems = driver.find_elements(By.CSS_SELECTOR, "h3[class*='e6cseyw2']")
            date_elems = driver.find_elements(By.CSS_SELECTOR, "span[class*='e6cseyw14']")
            
            count = len(review_elems)
            
            if count == 0:
                print(f"  └ {current_page}페이지에 수집 가능한 리뷰 요소가 없습니다.")
            else:
                for i in range(count):
                    # 상품명
                    if i < len(product_elems) and product_elems[i].text.strip():
                        p_name = product_elems[i].text.strip()
                    else:
                        p_name = main_title
                    
                    # 리뷰 본문
                    r_text = review_elems[i].text.strip().replace("\n", " ")
                    
                    # 날짜
                    if i < len(date_elems) and date_elems[i].text.strip():
                        d_text = date_elems[i].text.strip()
                    else:
                        d_text = ""
                    
                    writer.writerow([p_name, d_text, r_text])
                
                print(f"  └ {count}건 수집 완료")

            # 20페이지 수집 완료 시 종료
            if current_page == max_pages:
                break
            
            # 다음 페이지 이동
            next_page_num = current_page + 1
            moved = click_next_page(driver, next_page_num)
            if not moved:
                print(f"다음 페이지({next_page_num}) 이동 버튼을 클릭할 수 없습니다. 수집을 종료합니다.")
                break
            
            # 페이지 전환 후 데이터 로딩 대기
            time.sleep(random.uniform(2.5, 3.5))

    finally:
        file.close()
        driver.quit()
        print(f"\n작업 완료! 모든 데이터가 '{filename}' 파일에 성공적으로 저장되었습니다.")

if __name__ == "__main__":
    TARGET_URL = "https://www.kurly.com/goods/5026468"
    crawl_kurly_reviews(TARGET_URL, max_pages=20)