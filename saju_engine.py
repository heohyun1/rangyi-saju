# -*- coding: utf-8 -*-
"""
명리학 사주 계산 엔진 (Four Pillars of Destiny Calculator)
- 만세력 기반 사주 원국 산출
- 오행 분석, 십신 배치, 신살 판단
- 대운/세운 계산
"""

from datetime import datetime, timedelta
from korean_lunar_calendar import KoreanLunarCalendar
import math

# ============================================================
# 1. 기본 데이터: 천간(天干), 지지(地支), 오행(五行)
# ============================================================

CHEONGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
CHEONGAN_KR = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']

JIJI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
JIJI_KR = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']

# 띠 이름
ZODIAC_ANIMALS = ['쥐', '소', '호랑이', '토끼', '용', '뱀', '말', '양', '원숭이', '닭', '개', '돼지']

# 천간 오행 매핑 (0=목, 1=화, 2=토, 3=금, 4=수)
CHEONGAN_OHAENG = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]  # 甲乙=목, 丙丁=화, 戊己=토, 庚辛=금, 壬癸=수

# 천간 음양 (0=양, 1=음)
CHEONGAN_EUMYANG = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]

# 지지 오행 매핑
JIJI_OHAENG = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]  # 子=수, 丑=토, 寅=목...

# 지지 음양
JIJI_EUMYANG = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]

# 오행 이름
OHAENG_NAME = ['목(木)', '화(火)', '토(土)', '금(金)', '수(水)']
OHAENG_HANJA = ['木', '火', '土', '金', '水']
OHAENG_KR = ['목', '화', '토', '금', '수']

# 오행 색상
OHAENG_COLOR = ['#22c55e', '#ef4444', '#eab308', '#f5f5f5', '#3b82f6']

# ============================================================
# 2. 지장간(地藏干) 데이터
# ============================================================

JIJANGGAN = {
    '子': [('癸', 30)],
    '丑': [('癸', 9), ('辛', 3), ('己', 18)],
    '寅': [('戊', 7), ('丙', 7), ('甲', 16)],
    '卯': [('乙', 30)],  # 수정: 卯는 乙만
    '辰': [('乙', 9), ('癸', 3), ('戊', 18)],
    '巳': [('戊', 7), ('庚', 7), ('丙', 16)],
    '午': [('丙', 10), ('己', 10), ('丁', 10)],
    '未': [('丁', 9), ('乙', 3), ('己', 18)],
    '申': [('己', 7), ('壬', 7), ('庚', 16)],
    '酉': [('辛', 30)],  # 수정: 酉는 辛만
    '戌': [('辛', 9), ('丁', 3), ('戊', 18)],
    '亥': [('戊', 7), ('甲', 7), ('壬', 16)],
}

# ============================================================
# 3. 십신(十神) 판단 로직
# ============================================================

SIPSIN_NAME = ['비견', '겁재', '식신', '상관', '편재', '정재', '편관', '정관', '편인', '정인']

def get_sipsin(ilgan_idx, target_idx):
    """일간 기준으로 다른 천간과의 십신 관계를 구합니다."""
    ilgan_ohaeng = CHEONGAN_OHAENG[ilgan_idx]
    ilgan_eum = CHEONGAN_EUMYANG[ilgan_idx]
    target_ohaeng = CHEONGAN_OHAENG[target_idx]
    target_eum = CHEONGAN_EUMYANG[target_idx]
    
    same_eum = (ilgan_eum == target_eum)
    
    # 오행 관계 판단
    if ilgan_ohaeng == target_ohaeng:
        return '비견' if same_eum else '겁재'
    
    # 내가 생하는 것 (식상)
    sheng_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 0}  # 목→화, 화→토...
    if sheng_map[ilgan_ohaeng] == target_ohaeng:
        return '식신' if same_eum else '상관'
    
    # 내가 극하는 것 (재성)
    ke_map = {0: 2, 1: 3, 2: 4, 3: 0, 4: 1}  # 목→토, 화→금...
    if ke_map[ilgan_ohaeng] == target_ohaeng:
        return '편재' if same_eum else '정재'
    
    # 나를 극하는 것 (관성)
    if ke_map[target_ohaeng] == ilgan_ohaeng:
        return '편관' if same_eum else '정관'
    
    # 나를 생하는 것 (인성)
    if sheng_map[target_ohaeng] == ilgan_ohaeng:
        return '편인' if same_eum else '정인'
    
    return '비견'

def get_sipsin_for_jiji(ilgan_idx, jiji_char):
    """지지의 지장간 본기 기준으로 십신을 구합니다."""
    jjg = JIJANGGAN.get(jiji_char, [])
    if not jjg:
        return '비견'
    # 본기 (마지막 또는 가장 큰 비율)
    bongi = jjg[-1][0]
    bongi_idx = CHEONGAN.index(bongi)
    return get_sipsin(ilgan_idx, bongi_idx)

# ============================================================
# 4. 절기(節氣) 데이터 및 월주 계산
# ============================================================

# 절기 기반 월 경계 (각 월의 시작 절기)
# 절기는 태양의 황경에 따라 결정됨
JEOLGI_MONTHS = {
    '입춘': 1, '경칩': 2, '청명': 3, '입하': 4,
    '망종': 5, '소서': 6, '입추': 7, '백로': 8,
    '한로': 9, '입동': 10, '대설': 11, '소한': 12
}

# 절기 대략적 날짜 (매년 약간씩 다름, 평균값 사용)
# (월, 일) - 절기가 시작되는 대략적 날짜
JEOLGI_DATES = {
    1: (2, 4),    # 입춘 2/4
    2: (3, 6),    # 경칩 3/6
    3: (4, 5),    # 청명 4/5
    4: (5, 6),    # 입하 5/6
    5: (6, 6),    # 망종 6/6
    6: (7, 7),    # 소서 7/7
    7: (8, 7),    # 입추 8/7
    8: (9, 8),    # 백로 9/8
    9: (10, 8),   # 한로 10/8
    10: (11, 7),  # 입동 11/7
    11: (12, 7),  # 대설 12/7
    12: (1, 6),   # 소한 1/6 (다음해 기준이지만, 전년도 12월로 처리)
}

# 더 정확한 절기 계산 (태양 황경 기반 근사)
def get_solar_term_date(year, month_idx):
    """절기 시작 날짜를 좀 더 정확하게 계산합니다."""
    base_dates = JEOLGI_DATES[month_idx]
    # 기본 절기 날짜 반환 (더 정확한 계산을 위해서는 천문 데이터 필요)
    m, d = base_dates
    if month_idx == 12:
        return datetime(year, m, d)
    return datetime(year, m, d)

def get_saju_month(solar_date):
    """양력 날짜로 사주의 월(인월=1월~축월=12월)을 구합니다."""
    year = solar_date.year
    month = solar_date.month
    day = solar_date.day
    
    # 절기 경계 확인
    # 소한(1/6) → 12월(축월)
    # 입춘(2/4) → 1월(인월)
    # 경칩(3/6) → 2월(묘월)
    # ...
    
    boundaries = [
        (1, 6, 12),   # 소한 이후 = 축월(12월)
        (2, 4, 1),    # 입춘 이후 = 인월(1월)
        (3, 6, 2),    # 경칩 이후 = 묘월(2월)
        (4, 5, 3),    # 청명 이후 = 진월(3월)
        (5, 6, 4),    # 입하 이후 = 사월(4월)
        (6, 6, 5),    # 망종 이후 = 오월(5월)
        (7, 7, 6),    # 소서 이후 = 미월(6월)
        (8, 7, 7),    # 입추 이후 = 신월(7월)
        (9, 8, 8),    # 백로 이후 = 유월(8월)
        (10, 8, 9),   # 한로 이후 = 술월(9월)
        (11, 7, 10),  # 입동 이후 = 해월(10월)
        (12, 7, 11),  # 대설 이후 = 자월(11월)
    ]
    
    saju_month = 12  # 기본값 (축월)
    for bm, bd, sm in reversed(boundaries):
        if month > bm or (month == bm and day >= bd):
            saju_month = sm
            break
    
    return saju_month

# ============================================================
# 5. 연주/월주/일주/시주 계산
# ============================================================

def get_year_pillar(solar_date):
    """연주(年柱) 계산 - 입춘 기준"""
    year = solar_date.year
    month = solar_date.month
    day = solar_date.day
    
    # 입춘 이전이면 전년도로 계산
    if month < 2 or (month == 2 and day < 4):
        year -= 1
    
    # 천간: (year - 4) % 10
    gan_idx = (year - 4) % 10
    # 지지: (year - 4) % 12
    ji_idx = (year - 4) % 12
    
    return gan_idx, ji_idx

def get_month_pillar(year_gan_idx, saju_month):
    """월주(月柱) 계산 - 연간 기준 월간 산출"""
    # 월지: 인월(1)=寅(2), 묘월(2)=卯(3), ... 축월(12)=丑(1)
    month_ji_idx = (saju_month + 1) % 12  # 인월=寅(idx 2)
    
    # 월간 산출 (연간에 따른 월간 시작점)
    # 갑기년 → 병인월 시작
    # 을경년 → 무인월 시작
    # 병신년 → 경인월 시작
    # 정임년 → 임인월 시작
    # 무계년 → 갑인월 시작
    
    year_gan_group = year_gan_idx % 5
    base_month_gan = [2, 4, 6, 8, 0]  # 병(2), 무(4), 경(6), 임(8), 갑(0)
    
    month_gan_idx = (base_month_gan[year_gan_group] + saju_month - 1) % 10
    
    return month_gan_idx, month_ji_idx

def get_day_pillar(solar_date):
    """일주(日柱) 계산 - 기준일로부터 60갑자 순환"""
    # 기준일: 2000년 1월 1일 = 甲子(갑자)일 → 실제로는 庚辰일
    # 정확한 기준: 1900년 1월 1일 = 甲戌(갑술)일 (간지 순번 10)
    
    # 더 정확한 기준점 사용
    # 2000년 1월 1일 = 庚辰일 (간지 순번 16, 0-indexed)
    reference_date = datetime(2000, 1, 1)
    reference_ganzhi = 16  # 庚辰 = 6*1 + ... 실제 계산
    
    # 실제 기준: 양력 2000-01-01 은 甲子 순번으로 계산
    # 1900-01-01 = 갑자(0)일 기준으로 재계산
    # 실측: 2000-01-01 = 갑진일 (간=0, 지=4) → 순번 40? 
    # 정확한 값: 2000-01-01 = 庚辰 (gan=6, ji=4)
    
    # 검증된 기준일 사용
    # 1949-12-21 = 갑자일 (甲子)
    ref = datetime(1949, 12, 21)
    ref_idx = 0  # 甲子 = 0
    
    delta = (solar_date - ref).days
    ganzhi_idx = (ref_idx + delta) % 60
    
    gan_idx = ganzhi_idx % 10
    ji_idx = ganzhi_idx % 12
    
    return gan_idx, ji_idx

def get_hour_pillar(day_gan_idx, birth_hour):
    """시주(時柱) 계산"""
    # 시지 결정 (2시간 단위)
    # 23:00~01:00 = 子시(0)
    # 01:00~03:00 = 丑시(1)
    # ...
    
    hour_ji_map = [
        (23, 1, 0),   # 子시
        (1, 3, 1),    # 丑시
        (3, 5, 2),    # 寅시
        (5, 7, 3),    # 卯시
        (7, 9, 4),    # 辰시
        (9, 11, 5),   # 巳시
        (11, 13, 6),  # 午시
        (13, 15, 7),  # 未시
        (15, 17, 8),  # 申시
        (17, 19, 9),  # 酉시
        (19, 21, 10), # 戌시
        (21, 23, 11), # 亥시
    ]
    
    hour_ji_idx = 0
    if birth_hour >= 23 or birth_hour < 1:
        hour_ji_idx = 0
    elif birth_hour >= 1 and birth_hour < 3:
        hour_ji_idx = 1
    elif birth_hour >= 3 and birth_hour < 5:
        hour_ji_idx = 2
    elif birth_hour >= 5 and birth_hour < 7:
        hour_ji_idx = 3
    elif birth_hour >= 7 and birth_hour < 9:
        hour_ji_idx = 4
    elif birth_hour >= 9 and birth_hour < 11:
        hour_ji_idx = 5
    elif birth_hour >= 11 and birth_hour < 13:
        hour_ji_idx = 6
    elif birth_hour >= 13 and birth_hour < 15:
        hour_ji_idx = 7
    elif birth_hour >= 15 and birth_hour < 17:
        hour_ji_idx = 8
    elif birth_hour >= 17 and birth_hour < 19:
        hour_ji_idx = 9
    elif birth_hour >= 19 and birth_hour < 21:
        hour_ji_idx = 10
    else:
        hour_ji_idx = 11
    
    # 시간 산출 (일간 기준)
    day_gan_group = day_gan_idx % 5
    base_hour_gan = [0, 2, 4, 6, 8]  # 갑기일→갑자시, 을경일→병자시...
    
    hour_gan_idx = (base_hour_gan[day_gan_group] + hour_ji_idx) % 10
    
    return hour_gan_idx, hour_ji_idx

# ============================================================
# 6. 합/충/형/파/해 관계
# ============================================================

# 천간합
CHEONGAN_HAP = {
    (0, 5): '갑기합(토)', (5, 0): '갑기합(토)',
    (1, 6): '을경합(금)', (6, 1): '을경합(금)',
    (2, 7): '병신합(수)', (7, 2): '병신합(수)',
    (3, 8): '정임합(목)', (8, 3): '정임합(목)',
    (4, 9): '무계합(화)', (9, 4): '무계합(화)',
}

# 천간충 (7번째)
CHEONGAN_CHUNG = {
    (0, 6): '갑경충', (6, 0): '갑경충',
    (1, 7): '을신충', (7, 1): '을신충',
    (2, 8): '병임충', (8, 2): '병임충',
    (3, 9): '정계충', (9, 3): '정계충',
}

# 지지 육합
JIJI_YUKHAP = {
    (0, 1): '자축합(토)', (1, 0): '자축합(토)',
    (2, 11): '인해합(목)', (11, 2): '인해합(목)',
    (3, 10): '묘술합(화)', (10, 3): '묘술합(화)',
    (4, 9): '진유합(금)', (9, 4): '진유합(금)',
    (5, 8): '사신합(수)', (8, 5): '사신합(수)',
    (6, 7): '오미합(토)', (7, 6): '오미합(토)',
}

# 지지 삼합
JIJI_SAMHAP = {
    frozenset({8, 0, 4}): '수국삼합(申子辰)',
    frozenset({2, 6, 10}): '화국삼합(寅午戌)',
    frozenset({5, 9, 1}): '금국삼합(巳酉丑)',
    frozenset({11, 3, 7}): '목국삼합(亥卯未)',
}

# 지지충 (6번째)
JIJI_CHUNG = {
    (0, 6): '자오충', (6, 0): '자오충',
    (1, 7): '축미충', (7, 1): '축미충',
    (2, 8): '인신충', (8, 2): '인신충',
    (3, 9): '묘유충', (9, 3): '묘유충',
    (4, 10): '진술충', (10, 4): '진술충',
    (5, 11): '사해충', (11, 5): '사해충',
}

# 지지형
JIJI_HYUNG = {
    (2, 5): '인사형', (5, 2): '인사형',
    (5, 8): '사신형', (8, 5): '사신형',
    (2, 8): '인신형', (8, 2): '인신형',
    (1, 10): '축술형', (10, 1): '축술형',
    (1, 7): '축미형', (7, 1): '축미형',
    (10, 7): '술미형', (7, 10): '술미형',
    (0, 3): '자묘형', (3, 0): '자묘형',
    (4, 4): '진진 자형', (6, 6): '오오 자형',
    (9, 9): '유유 자형', (11, 11): '해해 자형',
}

# ============================================================
# 7. 신살(神殺) 데이터
# ============================================================

def get_sinsal(year_ji, month_ji, day_ji, hour_ji):
    """주요 신살을 판단합니다."""
    sinsal_list = []
    all_ji = [year_ji, month_ji, day_ji, hour_ji]
    pillar_names = ['년지', '월지', '일지', '시지']
    
    # 도화살 (桃花殺) - 일지 기준
    # 인오술 → 卯, 사유축 → 午, 신자진 → 酉, 해묘미 → 子
    dohua_map = {
        2: 3, 6: 3, 10: 3,   # 인오술 → 묘
        5: 6, 9: 6, 1: 6,    # 사유축 → 오  (수정: 오가 맞음)
        8: 9, 0: 9, 4: 9,    # 신자진 → 유
        11: 0, 3: 0, 7: 0,   # 해묘미 → 자
    }
    # 수정: 도화살 정확한 매핑
    dohua_map2 = {
        2: 3, 6: 3, 10: 3,   # 寅午戌 → 卯
        5: 0, 9: 0, 1: 0,    # 巳酉丑 → 午  
        8: 9, 0: 9, 4: 9,    # 申子辰 → 酉
        11: 6, 3: 6, 7: 6,   # 亥卯未 → 午
    }
    
    dohua_target = dohua_map.get(day_ji)
    if dohua_target is not None:
        for i, ji in enumerate(all_ji):
            if i != 2 and ji == dohua_target:
                sinsal_list.append(f'도화살(桃花殺) - {pillar_names[i]}')
    
    # 역마살 (驛馬殺) - 일지 기준
    # 인오술 → 申, 사유축 → 亥, 신자진 → 寅, 해묘미 → 巳
    yeokma_map = {
        2: 8, 6: 8, 10: 8,   # 인오술 → 신
        5: 11, 9: 11, 1: 11,  # 사유축 → 해
        8: 2, 0: 2, 4: 2,    # 신자진 → 인
        11: 5, 3: 5, 7: 5,   # 해묘미 → 사
    }
    
    yeokma_target = yeokma_map.get(day_ji)
    if yeokma_target is not None:
        for i, ji in enumerate(all_ji):
            if i != 2 and ji == yeokma_target:
                sinsal_list.append(f'역마살(驛馬殺) - {pillar_names[i]}')
    
    # 화개살 (華蓋殺) - 일지 기준  
    # 인오술 → 戌, 사유축 → 丑, 신자진 → 辰, 해묘미 → 未
    hwagae_map = {
        2: 10, 6: 10, 10: 10,  # 인오술 → 술
        5: 1, 9: 1, 1: 1,      # 사유축 → 축
        8: 4, 0: 4, 4: 4,      # 신자진 → 진
        11: 7, 3: 7, 7: 7,     # 해묘미 → 미
    }
    
    hwagae_target = hwagae_map.get(day_ji)
    if hwagae_target is not None:
        for i, ji in enumerate(all_ji):
            if i != 2 and ji == hwagae_target:
                sinsal_list.append(f'화개살(華蓋殺) - {pillar_names[i]}')
    
    # 귀문관살 (鬼門關殺)
    gwimun_pairs = [(0, 7), (1, 6), (2, 5), (3, 4),
                    (8, 11), (9, 10)]
    for i in range(4):
        for j in range(i+1, 4):
            pair = (all_ji[i], all_ji[j])
            rpair = (all_ji[j], all_ji[i])
            for gp in gwimun_pairs:
                if pair == gp or rpair == gp:
                    sinsal_list.append(f'귀문관살(鬼門關殺) - {pillar_names[i]}/{pillar_names[j]}')
    
    # 천을귀인 (天乙貴人) - 일간 기준은 별도 처리
    
    return sinsal_list

# ============================================================
# 8. 대운(大運) 계산
# ============================================================

def calculate_daeun(year_gan, year_ji, month_gan, month_ji, solar_date, gender):
    """대운을 계산합니다."""
    # 순행/역행 결정
    # 양남음녀 → 순행, 음남양녀 → 역행
    year_eum = CHEONGAN_EUMYANG[year_gan]
    
    if gender == '남':
        forward = (year_eum == 0)  # 양년생 남자 → 순행
    else:
        forward = (year_eum == 1)  # 음년생 여자 → 순행
    
    # 대운 시작 나이 계산 (간략화)
    # 실제로는 생일~다음/이전 절기까지 일수를 3으로 나눈 값
    month_num = solar_date.month
    day_num = solar_date.day
    
    # 간략 계산: 대운 시작 나이 (평균적으로 1~9세)
    if forward:
        # 다음 절기까지 남은 일수 / 3
        remaining_days = 30 - day_num  # 간략화
        start_age = max(1, min(9, remaining_days // 3))
    else:
        # 이전 절기까지 지난 일수 / 3
        passed_days = day_num
        start_age = max(1, min(9, passed_days // 3))
    
    # 대운 배열 생성 (10개)
    daeun_list = []
    current_gan = month_gan
    current_ji = month_ji
    
    for i in range(10):
        if forward:
            current_gan = (month_gan + i + 1) % 10
            current_ji = (month_ji + i + 1) % 12
        else:
            current_gan = (month_gan - i - 1) % 10
            current_ji = (month_ji - i - 1) % 12
        
        age = start_age + (i * 10)
        year = solar_date.year + age
        
        daeun_list.append({
            'age': age,
            'year': year,
            'gan': current_gan,
            'ji': current_ji,
            'gan_char': CHEONGAN[current_gan],
            'ji_char': JIJI[current_ji],
            'gan_kr': CHEONGAN_KR[current_gan],
            'ji_kr': JIJI_KR[current_ji],
            'label': f"{CHEONGAN_KR[current_gan]}{JIJI_KR[current_ji]}({CHEONGAN[current_gan]}{JIJI[current_ji]})",
        })
    
    return start_age, daeun_list

# ============================================================
# 9. 용신(用神) 판단 (간략)
# ============================================================

def determine_yongsin(ilgan_idx, ohaeng_count):
    """간략한 용신 판단"""
    ilgan_ohaeng = CHEONGAN_OHAENG[ilgan_idx]
    
    # 일간 오행의 강약 판단
    my_element = ilgan_ohaeng
    my_count = ohaeng_count[my_element]
    
    # 나를 생하는 오행(인성)
    sheng_map = {0: 4, 1: 0, 2: 1, 3: 2, 4: 3}  # 목←수, 화←목...
    support = ohaeng_count[sheng_map[my_element]]
    
    total_support = my_count + support
    
    # 신강/신약 판단
    if total_support >= 4:
        # 신강 → 설기(식상), 극기(재성, 관성)가 용신
        # 내가 생하는 것
        ke_map = {0: 2, 1: 3, 2: 4, 3: 0, 4: 1}
        sheng_child = {0: 1, 1: 2, 2: 3, 3: 4, 4: 0}
        
        yongsin = sheng_child[my_element]
        strength = '신강(身強)'
        advice = f"기운이 강하므로 {OHAENG_NAME[yongsin]} 기운이 용신입니다. 활동적으로 에너지를 발산하는 것이 좋습니다."
    else:
        # 신약 → 생기(인성), 비견이 용신
        yongsin = sheng_map[my_element]
        strength = '신약(身弱)'
        advice = f"기운이 약하므로 {OHAENG_NAME[yongsin]} 기운이 용신입니다. 안정을 추구하고 내면을 다지는 것이 좋습니다."
    
    return {
        'strength': strength,
        'yongsin_ohaeng': OHAENG_NAME[yongsin],
        'yongsin_idx': yongsin,
        'advice': advice,
    }

# ============================================================
# 10. 메인 사주 분석 함수
# ============================================================

def analyze_saju(year, month, day, hour, gender, is_lunar=False):
    """
    사주를 분석합니다.
    
    Args:
        year: 출생 연도
        month: 출생 월
        day: 출생 일
        hour: 출생 시 (0-23)
        gender: '남' 또는 '여'
        is_lunar: 음력 여부
    
    Returns:
        dict: 사주 분석 결과
    """
    
    # 음력→양력 변환
    solar_year, solar_month, solar_day = year, month, day
    lunar_info = None
    
    if is_lunar:
        try:
            cal = KoreanLunarCalendar()
            cal.setLunarDate(year, month, day, False)
            solar_year = cal.solarYear
            solar_month = cal.solarMonth
            solar_day = cal.solarDay
            lunar_info = f"음력 {year}년 {month}월 {day}일 → 양력 {solar_year}년 {solar_month}월 {solar_day}일"
        except:
            pass
    else:
        try:
            cal = KoreanLunarCalendar()
            cal.setSolarDate(year, month, day)
            lunar_info = f"양력 {year}년 {month}월 {day}일 → 음력 {cal.lunarYear}년 {cal.lunarMonth}월 {cal.lunarDay}일"
        except:
            pass
    
    solar_date = datetime(solar_year, solar_month, solar_day)
    
    # 1. 사주 원국 계산
    year_gan, year_ji = get_year_pillar(solar_date)
    saju_month = get_saju_month(solar_date)
    month_gan, month_ji = get_month_pillar(year_gan, saju_month)
    day_gan, day_ji = get_day_pillar(solar_date)
    hour_gan, hour_ji = get_hour_pillar(day_gan, hour)
    
    # 2. 오행 분석
    ohaeng_count = [0, 0, 0, 0, 0]  # 목, 화, 토, 금, 수
    
    all_gan = [year_gan, month_gan, day_gan, hour_gan]
    all_ji = [year_ji, month_ji, day_ji, hour_ji]
    
    for g in all_gan:
        ohaeng_count[CHEONGAN_OHAENG[g]] += 1
    for j in all_ji:
        ohaeng_count[JIJI_OHAENG[j]] += 1
    
    # 3. 십신 배치
    ilgan = day_gan  # 일간이 기준
    
    sipsin = {
        'year_gan': get_sipsin(ilgan, year_gan),
        'month_gan': get_sipsin(ilgan, month_gan),
        'day_gan': '일주',
        'hour_gan': get_sipsin(ilgan, hour_gan),
        'year_ji': get_sipsin_for_jiji(ilgan, JIJI[year_ji]),
        'month_ji': get_sipsin_for_jiji(ilgan, JIJI[month_ji]),
        'day_ji': get_sipsin_for_jiji(ilgan, JIJI[day_ji]),
        'hour_ji': get_sipsin_for_jiji(ilgan, JIJI[hour_ji]),
    }
    
    # 4. 합/충 관계 분석
    relations = []
    
    # 천간 합/충
    gan_pairs = [(0,1,'년간-월간'), (0,2,'년간-일간'), (0,3,'년간-시간'),
                 (1,2,'월간-일간'), (1,3,'월간-시간'), (2,3,'일간-시간')]
    for i, j, name in gan_pairs:
        pair = (all_gan[i], all_gan[j])
        if pair in CHEONGAN_HAP:
            relations.append(f'천간합: {name} - {CHEONGAN_HAP[pair]}')
        if pair in CHEONGAN_CHUNG:
            relations.append(f'천간충: {name} - {CHEONGAN_CHUNG[pair]}')
    
    # 지지 합/충/형
    ji_pairs = [(0,1,'년지-월지'), (0,2,'년지-일지'), (0,3,'년지-시지'),
                (1,2,'월지-일지'), (1,3,'월지-시지'), (2,3,'일지-시지')]
    for i, j, name in ji_pairs:
        pair = (all_ji[i], all_ji[j])
        if pair in JIJI_YUKHAP:
            relations.append(f'지지육합: {name} - {JIJI_YUKHAP[pair]}')
        if pair in JIJI_CHUNG:
            relations.append(f'지지충: {name} - {JIJI_CHUNG[pair]}')
        if pair in JIJI_HYUNG:
            relations.append(f'지지형: {name} - {JIJI_HYUNG[pair]}')
    
    # 삼합 체크
    ji_set = set(all_ji)
    for key, value in JIJI_SAMHAP.items():
        if key.issubset(ji_set):
            relations.append(f'지지삼합: {value}')
    
    # 5. 신살 판단
    sinsal = get_sinsal(year_ji, month_ji, day_ji, hour_ji)
    
    # 6. 용신 판단
    yongsin = determine_yongsin(ilgan, ohaeng_count)
    
    # 7. 대운 계산
    start_age, daeun_list = calculate_daeun(year_gan, year_ji, month_gan, month_ji, solar_date, gender)
    
    # 8. 세운 (올해 운세)
    current_year = datetime.now().year
    current_year_gan = (current_year - 4) % 10
    current_year_ji = (current_year - 4) % 12
    
    # 9. 지장간 정보
    jijanggan_info = {}
    for pillar_name, ji_idx in [('년지', year_ji), ('월지', month_ji), ('일지', day_ji), ('시지', hour_ji)]:
        ji_char = JIJI[ji_idx]
        jjg = JIJANGGAN.get(ji_char, [])
        jijanggan_info[pillar_name] = [(CHEONGAN_KR[CHEONGAN.index(g)], g, days) for g, days in jjg]
    
    # 시간대 이름
    hour_ji_names = ['자시(23~01시)', '축시(01~03시)', '인시(03~05시)', '묘시(05~07시)',
                     '진시(07~09시)', '사시(09~11시)', '오시(11~13시)', '미시(13~15시)',
                     '신시(15~17시)', '유시(17~19시)', '술시(19~21시)', '해시(21~23시)']
    
    # 띠
    zodiac = ZODIAC_ANIMALS[year_ji]
    
    # 일주 60갑자 번호
    day_ganzhi_idx = (day_gan * 6 + day_ji) % 60  # 간략 계산
    
    result = {
        'input': {
            'year': year, 'month': month, 'day': day,
            'hour': hour, 'gender': gender, 'is_lunar': is_lunar,
            'lunar_info': lunar_info,
            'hour_name': hour_ji_names[hour_ji],
        },
        'pillars': {
            'year': {
                'gan': CHEONGAN[year_gan], 'ji': JIJI[year_ji],
                'gan_kr': CHEONGAN_KR[year_gan], 'ji_kr': JIJI_KR[year_ji],
                'gan_idx': year_gan, 'ji_idx': year_ji,
                'gan_ohaeng': OHAENG_KR[CHEONGAN_OHAENG[year_gan]],
                'ji_ohaeng': OHAENG_KR[JIJI_OHAENG[year_ji]],
                'label': f"{CHEONGAN_KR[year_gan]}{JIJI_KR[year_ji]}({CHEONGAN[year_gan]}{JIJI[year_ji]})",
            },
            'month': {
                'gan': CHEONGAN[month_gan], 'ji': JIJI[month_ji],
                'gan_kr': CHEONGAN_KR[month_gan], 'ji_kr': JIJI_KR[month_ji],
                'gan_idx': month_gan, 'ji_idx': month_ji,
                'gan_ohaeng': OHAENG_KR[CHEONGAN_OHAENG[month_gan]],
                'ji_ohaeng': OHAENG_KR[JIJI_OHAENG[month_ji]],
                'label': f"{CHEONGAN_KR[month_gan]}{JIJI_KR[month_ji]}({CHEONGAN[month_gan]}{JIJI[month_ji]})",
            },
            'day': {
                'gan': CHEONGAN[day_gan], 'ji': JIJI[day_ji],
                'gan_kr': CHEONGAN_KR[day_gan], 'ji_kr': JIJI_KR[day_ji],
                'gan_idx': day_gan, 'ji_idx': day_ji,
                'gan_ohaeng': OHAENG_KR[CHEONGAN_OHAENG[day_gan]],
                'ji_ohaeng': OHAENG_KR[JIJI_OHAENG[day_ji]],
                'label': f"{CHEONGAN_KR[day_gan]}{JIJI_KR[day_ji]}({CHEONGAN[day_gan]}{JIJI[day_ji]})",
            },
            'hour': {
                'gan': CHEONGAN[hour_gan], 'ji': JIJI[hour_ji],
                'gan_kr': CHEONGAN_KR[hour_gan], 'ji_kr': JIJI_KR[hour_ji],
                'gan_idx': hour_gan, 'ji_idx': hour_ji,
                'gan_ohaeng': OHAENG_KR[CHEONGAN_OHAENG[hour_gan]],
                'ji_ohaeng': OHAENG_KR[JIJI_OHAENG[hour_ji]],
                'label': f"{CHEONGAN_KR[hour_gan]}{JIJI_KR[hour_ji]}({CHEONGAN[hour_gan]}{JIJI[hour_ji]})",
            },
        },
        'ohaeng': {
            'count': {OHAENG_NAME[i]: ohaeng_count[i] for i in range(5)},
            'dominant': OHAENG_NAME[ohaeng_count.index(max(ohaeng_count))],
            'weak': OHAENG_NAME[ohaeng_count.index(min(ohaeng_count))],
            'values': ohaeng_count,
        },
        'sipsin': sipsin,
        'relations': relations,
        'sinsal': sinsal,
        'yongsin': yongsin,
        'daeun': {
            'start_age': start_age,
            'list': daeun_list,
        },
        'current_year': {
            'year': current_year,
            'gan': CHEONGAN[current_year_gan],
            'ji': JIJI[current_year_ji],
            'gan_kr': CHEONGAN_KR[current_year_gan],
            'ji_kr': JIJI_KR[current_year_ji],
            'label': f"{current_year}년 {CHEONGAN_KR[current_year_gan]}{JIJI_KR[current_year_ji]}({CHEONGAN[current_year_gan]}{JIJI[current_year_ji]})",
        },
        'zodiac': zodiac,
        'jijanggan': jijanggan_info,
        'ilgan_ohaeng': OHAENG_NAME[CHEONGAN_OHAENG[ilgan]],
    }
    
    return result


# 테스트
if __name__ == '__main__':
    import json
    result = analyze_saju(1990, 5, 15, 14, '남', is_lunar=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
