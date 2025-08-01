사이트 주소 https://www.pimfyvirus.com/ <- 여기서 임보 동물 찾기에서 강아지와 고양이 정보 json파일로 분리 저장 

강아지와 고양이 정보 분리 저장 및 분석 진행 
현재 상태: 임보중,임보가능,입양완료,공고종료 tag 크게 4가지로 분류 

data 폴더 구조 
    - _id.txt -> 임보중,임보가능 tag id만 추출  \n
    - _info.json -> id에 따른 상세정보(이미지,이름,나이,성별,구조지역 등등) \n
    - _data.json -> 임보중,임보가능,입양완료,공고종료 4가지 tag 모두 저장(id,이름,성별,몸무게 등등) \n
                    이에따른 데이터 시각화완료(dog,cat_data_scraping.ipynb) 

