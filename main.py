import argparse
import requests
import json
from dotenv import load_dotenv
import os
load_dotenv()

def get_access_token(consumer_key:str, consumer_secret:str):
    end_point_url = ("https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json?"
                     f"consumer_key={consumer_key}&consumer_secret={consumer_secret}")

    response = requests.get(end_point_url)
    data = response.json()
    access_token = data["result"]["accessToken"]

    return access_token

def get_data_from_api(adm_cd:str, year:str):
    # from dotenv import load_dotenv
    # import os
    # load_dotenv()

    if not hasattr(get_data_from_api, "access_token"):
        consumer_key = os.getenv("CONSUMER_KEY")
        consumer_secret = os.getenv("CONSUMER_SECRET")
        get_data_from_api.access_token = get_access_token(
            consumer_key, consumer_secret
        )
        print("새로운 인증 토큰을 발급받았습니다.")

    access_token = get_data_from_api.access_token
    low_search = 1

    # 데이터 요청
    end_point_url = ("https://sgisapi.mods.go.kr/OpenAPI3/stats/population.json?"
                     f"accessToken={access_token}&year={year}&adm_cd={adm_cd}&low_search={low_search}")

    response = requests.get(end_point_url)
    response_json = response.json()

    err_cd = response_json.get("errCd")
    err_msg = response_json.get("errMsg")

    if err_cd != 0:
        if err_cd == "-401":
            print("토큰이 만료되어 재발급을 시도합니다.")
            consumer_key = os.getenv("CONSUMER_KEY")
            consumer_secret = os.getenv("CONSUMER_SECRET")
            get_data_from_api.access_token = get_access_token(
                consumer_key, consumer_secret
            )
            # 재귀적으로 함수를 다시 호출하여 데이터 가져오기
            return get_data_from_api(adm_cd, year)
        if err_msg == "검색결과가 존재하지 않습니다.":
            return None
        else:
            raise Exception(f"API 에러 발생 [errCd: {err_cd}, errMsg: {err_msg}]")

    result_data = response_json["result"]
    # print(json.dumps(result_data, indent=4, ensure_ascii=False))
    return result_data

def save_file(content, file_name, file_type):
    import jsonlines

    if file_type == "json":
        with jsonlines.open(file_name, "w") as f:
            f.write_all(content)

def upload_to_s3(file_name, bucket_name, object_name):
    from botocore.exceptions import NoCredentialsError
    import boto3

    s3_client = boto3.client("s3",
                      aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                      aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                      region_name=os.getenv("AWS_DEFAULT_REGION"))

    try:
        s3_client.upload_file(file_name, bucket_name, object_name)
    except NoCredentialsError:
        print("AWS 자격 증명을 찾을 수 없습니다.")

def main():
    parser = argparse.ArgumentParser(
        description="인구 통계 API"
    )
    parser.add_argument(
        "-i",
        "--initialization",
        required=True,
        help="데이터 수집 초기 여부 (y/n)",
    )
    parser.add_argument(
        "-a", "--adm_cd", type=str, help="행정구역코드"
    )
    parser.add_argument("-y", "--year", type=str, help="기준연도")

    args = parser.parse_args()

    init_yn = args.initialization
    adm_cd = args.adm_cd
    year = args.year

    file_type = "json" 
    bucket_name = "metacode-realestate-test"
    # object_name = f"apt-trade-raw/deal_ymd={deal_ymd}/lawd_cd={lawd_cd}/result.json"

    if init_yn == "y":
        list_adm_cd = [
            "11110"  # 종로구
            , "11140"  # 중구
            , "11170"  # 용산구
            , "11200"  # 성동구
            , "11215"  # 광진구
            , "11230"  # 동대문구
            , "11260"  # 중랑구
            , "11290"  # 성북구
            , "11305"  # 강북구
            , "11320"  # 도봉구
            , "11350"  # 노원구
            , "11380"  # 은평구
            , "11410"  # 서대문구
            , "11440"  # 마포구
            , "11470"  # 양천구
            , "11500"  # 강서구
            , "11530"  # 구로구
            , "11545"  # 금천구
            , "11560"  # 영등포구
            , "11590"  # 동작구
            , "11620"  # 관악구
            , "11650"  # 서초구
            , "11680"  # 강남구
            , "11710"  # 송파구
            , "11740"  # 강동구
        ]

        years = list(range(2015, 2024))

        for target_year in years:
            for target_adm_cd in list_adm_cd:
                result_json = get_data_from_api(target_adm_cd, target_year)

                file_name = f"{target_year}_{target_adm_cd}_result.json"

                if result_json is not None:
                    save_file(result_json, file_name, file_type)
                    upload_to_s3(file_name, bucket_name, object_name)
                else:
                    with open(file_name, "w", encoding="utf-8") as f:
                        pass

    elif init_yn == "n":
        if not adm_cd or not year:
            raise ValueError(
                "-i가 'n'일 경우 -a(행정구역코드)와 -y(기준연도)는 필수 입력값입니다."
            )

        # print(f"개별 수집 모드: 행정구역코드={adm_cd}, 기준연도={year}")
        result_json = get_data_from_api(adm_cd, year)
        file_name = f"{target_year}_{target_adm_cd}_result.json"

        if result_json is not None:
            save_file(result_json, file_name, file_type)
            upload_to_s3(file_name, bucket_name, object_name)
        else:
            with open(file_name, "w", encoding="utf-8") as f:
                pass

    else:
        raise Exception("올바른 값을 입력하세요. (y/n)")


if __name__ == "__main__":
    main()