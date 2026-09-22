import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. 환경변수 로드 및 기본 설정
# ---------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("SEOUL_DATA_API_KEY")

if not API_KEY:
    raise ValueError("API Key가 설정되지 않았습니다. .env 파일의 SEOUL_DATA_API_KEY를 확인하세요.")

SERVICE_NAME = "VwsmTrdarSelngQq"
BASE_URL = f"http://openapi.seoul.go.kr:8088/{API_KEY}/json/{SERVICE_NAME}"
BATCH_SIZE = 1000  # API 1회 호출 최대 제한

# 수집 대상 분기 (2024년 1분기 ~ 2026년 2분기)
TARGET_QUARTERS = [
    "20241", "20242", "20243", "20244",
    "20251", "20252", "20253", "20254",
    "20261", "20262"
]

OUTPUT_DIR = "./seoul_sales_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------
# 2. 분기별 데이터 수집 함수
# ---------------------------------------------------------
def fetch_quarter_data(quarter_cd: str):
    """
    특정 분기(quarter_cd)의 모든 데이터를 페이징 처리하여 수집합니다.
    """
    print(f"\n[수집 시작] 분기: {quarter_cd}")
    
    # 1. 전체 데이터 개수 조회를 위한 최초 호출 (1 ~ 1)
    init_url = f"{BASE_URL}/1/1/{quarter_cd}"
    try:
        response = requests.get(init_url, timeout=10)
        res_json = response.json()
    except Exception as e:
        print(f"  [오류] API 최초 접속 실패 ({quarter_cd}): {e}")
        return [], 0

    # API 응답 결과 확인
    if SERVICE_NAME not in res_json:
        result_msg = res_json.get("RESULT", {}).get("MESSAGE", "데이터 없음/오류")
        print(f"  [알림] 분기 {quarter_cd} 데이터 없음 또는 오류: {result_msg}")
        return [], 0

    total_count = res_json[SERVICE_NAME]["list_total_count"]
    print(f"  [정보] API 조회 건수 (list_total_count): {total_count:,}건")

    if total_count == 0:
        return [], 0

    # 2. BATCH_SIZE 단위로 루프를 돌며 전체 데이터 수집
    collected_rows = []
    for start_idx in range(1, total_count + 1, BATCH_SIZE):
        end_idx = min(start_idx + BATCH_SIZE - 1, total_count)
        url = f"{BASE_URL}/{start_idx}/{end_idx}/{quarter_cd}"
        
        retry_count = 0
        success = False
        
        while retry_count < 3 and not success:
            try:
                res = requests.get(url, timeout=10)
                data = res.json()
                
                if SERVICE_NAME in data and "row" in data[SERVICE_NAME]:
                    rows = data[SERVICE_NAME]["row"]
                    collected_rows.extend(rows)
                    success = True
                else:
                    retry_count += 1
                    time.sleep(1)
            except Exception as req_err:
                retry_count += 1
                time.sleep(1)

        if not success:
            print(f"  [경고] {start_idx}~{end_idx} 구간 수집 실패")

        # API 서버 부하 방지를 위한 미세 대기
        time.sleep(0.05)

    print(f"  [수집 완료] 메모리 로드 건수: {len(collected_rows):,}건")
    return collected_rows, total_count


# ---------------------------------------------------------
# 3. 데이터 저장 및 검증 함수
# ---------------------------------------------------------
def process_and_verify():
    verification_summary = []
    all_quarters_data = []

    for quarter in TARGET_QUARTERS:
        # 1) 데이터 수집
        rows, api_total_count = fetch_quarter_data(quarter)
        collected_count = len(rows)

        saved_count = 0
        status = "FAIL"

        if collected_count > 0:
            df_quarter = pd.DataFrame(rows)
            
            # 개별 분기 파일 저장
            file_path = os.path.join(OUTPUT_DIR, f"seoul_sales_{quarter}.csv")
            df_quarter.to_csv(file_path, index=False, encoding="utf-8-sig")
            
            # 2) 저장 검증: 저장된 파일 재로드 후 행 수 검증
            saved_df = pd.read_csv(file_path)
            saved_count = len(saved_df)
            
            all_quarters_data.append(df_quarter)

            # API 제공 개수, 메모리 수집 개수, CSV 저장 개수 일치 여부 확인
            if api_total_count == collected_count == saved_count:
                status = "SUCCESS (일치)"
            else:
                status = "MISMATCH (불일치)"
        else:
            if api_total_count == 0:
                status = "NO DATA (미개설/미공개)"

        # 검증 결과 기재
        verification_summary.append({
            "TARGET_QUARTER": quarter,
            "API_TOTAL_COUNT": api_total_count,
            "COLLECTED_COUNT": collected_count,
            "SAVED_CSV_COUNT": saved_count,
            "VERIFICATION_STATUS": status
        })

    # 전체 기간 병합 파일 저장
    if all_quarters_data:
        merged_df = pd.concat(all_quarters_data, ignore_index=True)
        merged_file_path = os.path.join(OUTPUT_DIR, "seoul_sales_20241_20262_master.csv")
        merged_df.to_csv(merged_file_path, index=False, encoding="utf-8-sig")
        print(f"\n[통합 저장] 전체 수집 데이터 통합 파일 저장 완료: {merged_file_path}")

    # ---------------------------------------------------------
    # 4. 검증 결과 종합 출력
    # ---------------------------------------------------------
    print("\n=========================================================================================")
    print("                              데이터 수집 및 저장 검증 보고서                              ")
    print("=========================================================================================")
    
    summary_df = pd.DataFrame(verification_summary)
    
    # 숫자에 쉼표 포맷 적용하여 출력
    display_df = summary_df.copy()
    display_df["API_TOTAL_COUNT"] = display_df["API_TOTAL_COUNT"].apply(lambda x: f"{x:,}")
    display_df["COLLECTED_COUNT"] = display_df["COLLECTED_COUNT"].apply(lambda x: f"{x:,}")
    display_df["SAVED_CSV_COUNT"] = display_df["SAVED_CSV_COUNT"].apply(lambda x: f"{x:,}")
    
    print(display_df.to_string(index=False))
    print("=========================================================================================")

    # 총계 출력
    tot_api = summary_df["API_TOTAL_COUNT"].sum()
    tot_collected = summary_df["COLLECTED_COUNT"].sum()
    tot_saved = summary_df["SAVED_CSV_COUNT"].sum()
    print(f"총 합계 | API 조회: {tot_api:,}건 | 메모리 수집: {tot_collected:,}건 | CSV 저장: {tot_saved:,}건")
    
    return summary_df


if __name__ == "__main__":
    process_and_verify()
    