# 필요한 패키지 / 도구 임폴트
from selenium import webdriver
from selenium.webdriver.common.by import By

# Chrome 브라우저를 자동 조작하기 위한 '아바타 브라우저' 생성
driver = webdriver.Chrome()

# 3 이동하고 싶은 웹사이트 주소: 교보문고, 물고기는 존재하지 않느다
url = 'https://product.kyobobook.co.kr/detail/S000001925800'

try:
    # 페이지 이동
    driver.get(url)

    #  F12로 복사한 selector 주소
    # selector = '#bookBasicInfo > section > div.border-t-1 > table > tbody > tr:nth-child(3) > td > div > span'
    # selector = '#bookBasicInfo span'
    selector = 'div.flex.flex-wrap.items-center.gap-2 > span'

    # selector 주소에 해당하는 '요소(element)'를 찾아서 변수에 저장
    element = driver.find_element(By.CSS_SELECTOR, selector)

# 찾은 요소에서 text 추출
    page_info = element.text.split(' |')[0]

    print(f"도서 쪽수: {page_info}")

except Exception as e:
    print(f"에러 발생: {e}")
