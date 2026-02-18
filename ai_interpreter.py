# -*- coding: utf-8 -*-
"""
AI 해석 엔진 (서버사이드 전용)
사용자에게는 API 정보가 일절 노출되지 않음
★ 429 자동 재시도 + 최신 모델 자동 전환 (2025년 기준)
"""

import os
import time
import requests

# ============================================================
# Gemini API 설정 (2025~2026 최신 모델명)
# ============================================================
# gemini-1.5-flash, gemini-pro는 2025년 4월 폐기됨 (404 뜸)
# gemini-2.0-flash/lite는 2026년 3월 31일 폐기 예정
# 현재 권장: gemini-2.5-flash 또는 gemini-2.0-flash
GEMINI_MODELS = [
    'gemini-2.0-flash',         # 무료 티어 기본 (가장 안정적)
    'gemini-2.0-flash-lite',    # 더 가벼운 버전 (무료)
    'gemini-2.5-flash-lite',    # 최신 경량 모델
    'gemini-2.5-flash',         # 최신 고성능
]

GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models'

# 마지막으로 성공한 모델 캐싱 (서버 재시작까지 유지)
_working_model = None

def get_api_key():
    return os.environ.get('GEMINI_API_KEY', '')

# ============================================================
# 명리학 해석 프롬프트
# ============================================================
SAJU_SYSTEM_PROMPT = """당신은 '랑이명리'의 전문 명리학 상담사입니다.
40년 경력의 정통 명리학 대가로서, 적천수(滴天髓), 자평진전(子平眞詮), 궁통보감(窮通寶鑑)을 깊이 연구한 전문가입니다.
따뜻하고 친근하면서도 전문적인 톤으로 사주를 해석합니다.

[해석 원칙]
1. 반드시 제공된 사주 데이터만을 기반으로 해석할 것 (창작/날조 금지)
2. 일간(日干)을 중심으로 다른 7글자와의 관계를 분석
3. 오행의 균형/불균형, 용신, 십신 배치를 종합적으로 판단
4. 합/충/형 관계가 있으면 그 영향을 구체적으로 설명
5. 신살이 있으면 현대적 관점에서 재해석
6. 대운의 흐름에 따른 시기별 변화를 설명
7. 긍정적이면서도 현실적인 조언을 포함
8. 전문 용어를 쓰되 괄호 안에 쉬운 설명을 병기
9. 미신적/공포 유발 표현은 절대 사용 금지
10. 자연스럽고 따뜻한 톤으로 상담하듯 작성

[해석 구조]
1. 타고난 성격과 기질 (일주 기반)
2. 재물운/직업운 (재성, 관성, 식상 분석)
3. 대인관계/연애운 (합충 관계, 도화살 등)
4. 건강 주의점 (오행 불균형 기반)
5. 올해 운세 (세운과 원국의 관계)
6. 대운 흐름 요약 (주요 전환점)
7. 종합 조언 (용신 활용법)

응답은 반드시 한국어로, 2000자 이상 상세하게 작성하세요.
"""


def build_saju_prompt(saju_data):
    """사주 데이터를 AI 해석용 프롬프트로 변환"""
    p = saju_data['pillars']
    
    prompt = f"""
다음 사주를 정통 명리학 관점에서 상세히 해석해주세요.

[기본 정보]
- 성별: {saju_data['input']['gender']}
- 생년월일시: {saju_data['input']['year']}년 {saju_data['input']['month']}월 {saju_data['input']['day']}일 {saju_data['input']['hour_name']}
- 띠: {saju_data['zodiac']}띠

[사주 원국 (四柱八字)]
- 년주(年柱): {p['year']['label']} | 천간: {p['year']['gan_ohaeng']} | 지지: {p['year']['ji_ohaeng']}
- 월주(月柱): {p['month']['label']} | 천간: {p['month']['gan_ohaeng']} | 지지: {p['month']['ji_ohaeng']}
- 일주(日柱): {p['day']['label']} | 천간: {p['day']['gan_ohaeng']} | 지지: {p['day']['ji_ohaeng']}  ← 일간(나)
- 시주(時柱): {p['hour']['label']} | 천간: {p['hour']['gan_ohaeng']} | 지지: {p['hour']['ji_ohaeng']}

[일간] {p['day']['gan_kr']}({p['day']['gan']}) = {saju_data['ilgan_ohaeng']}

[오행 분포]
목(木):{saju_data['ohaeng']['values'][0]} 화(火):{saju_data['ohaeng']['values'][1]} 토(土):{saju_data['ohaeng']['values'][2]} 금(金):{saju_data['ohaeng']['values'][3]} 수(水):{saju_data['ohaeng']['values'][4]}
강: {saju_data['ohaeng']['dominant']} | 약: {saju_data['ohaeng']['weak']}

[십신 배치]
년간 {p['year']['gan_kr']}: {saju_data['sipsin']['year_gan']} | 년지 {p['year']['ji_kr']}: {saju_data['sipsin']['year_ji']}
월간 {p['month']['gan_kr']}: {saju_data['sipsin']['month_gan']} | 월지 {p['month']['ji_kr']}: {saju_data['sipsin']['month_ji']}
일지 {p['day']['ji_kr']}: {saju_data['sipsin']['day_ji']}
시간 {p['hour']['gan_kr']}: {saju_data['sipsin']['hour_gan']} | 시지 {p['hour']['ji_kr']}: {saju_data['sipsin']['hour_ji']}

[신강/신약] {saju_data['yongsin']['strength']}
[용신] {saju_data['yongsin']['yongsin_ohaeng']}

[합/충/형]
{chr(10).join(saju_data['relations']) if saju_data['relations'] else '없음'}

[신살]
{chr(10).join(saju_data['sinsal']) if saju_data['sinsal'] else '없음'}

[대운] {saju_data['daeun']['start_age']}세 시작
{chr(10).join([f"- {d['age']}세~: {d['label']}" for d in saju_data['daeun']['list']])}

[올해 세운] {saju_data['current_year']['label']}

위 정보를 바탕으로 종합적이고 상세한 사주 해석을 작성해주세요.
"""
    return prompt


def _call_gemini(prompt, extra_prompt='', max_tokens=4096, timeout=60):
    """
    Gemini API 호출
    - 429(한도초과) → 대기 후 재시도 (최대 3회)
    - 404(모델없음) → 다음 모델로 자동 전환
    - 성공한 모델 기억하여 다음 호출부터 바로 사용
    """
    global _working_model
    
    api_key = get_api_key()
    if not api_key:
        return {
            'success': False,
            'error': 'GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.',
            'interpretation': None
        }
    
    full_prompt = prompt + extra_prompt
    
    # 모델 순서: 마지막 성공한 모델 먼저
    if _working_model:
        models = [_working_model] + [m for m in GEMINI_MODELS if m != _working_model]
    else:
        models = GEMINI_MODELS[:]
    
    last_error = ''
    
    for model in models:
        url = f'{GEMINI_BASE_URL}/{model}:generateContent'
        
        # 429 재시도 (최대 3회, 5초→15초→30초 대기)
        for attempt in range(3):
            try:
                wait = [0, 5, 15][attempt]
                if wait > 0:
                    print(f"[AI] 대기 {wait}초... (재시도 {attempt+1}/3)")
                    time.sleep(wait)
                
                print(f"[AI] 호출: {model} (시도 {attempt+1})")
                
                response = requests.post(
                    url,
                    headers={
                        'Content-Type': 'application/json',
                        'x-goog-api-key': api_key,
                    },
                    json={
                        'system_instruction': {
                            'parts': [{'text': SAJU_SYSTEM_PROMPT}]
                        },
                        'contents': [{
                            'parts': [{'text': full_prompt}]
                        }],
                        'generationConfig': {
                            'temperature': 0.7,
                            'topP': 0.9,
                            'topK': 40,
                            'maxOutputTokens': max_tokens,
                        }
                    },
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    _working_model = model
                    print(f"[AI] ✅ 성공! 모델: {model}, {len(text)}자")
                    return {'success': True, 'interpretation': text, 'error': None}
                
                elif response.status_code == 429:
                    print(f"[AI] 429 한도초과 ({model}, 시도 {attempt+1})")
                    last_error = 'API 호출 한도 초과(429). 무료 티어 분당 15회 제한. 잠시 후 다시 시도해주세요.'
                    continue  # 같은 모델 재시도
                
                elif response.status_code == 404:
                    print(f"[AI] 404 - {model} 사용 불가, 다음 모델 시도")
                    last_error = f'{model} 모델을 사용할 수 없습니다.'
                    break  # 다음 모델로
                
                elif response.status_code == 403:
                    err = response.text[:200]
                    print(f"[AI] 403 권한없음: {err}")
                    return {
                        'success': False,
                        'error': 'API 키가 유효하지 않습니다. Google AI Studio에서 새 키를 발급하세요.',
                        'interpretation': None
                    }
                
                else:
                    err = response.text[:200]
                    print(f"[AI] {response.status_code}: {err}")
                    last_error = f'API 오류 ({response.status_code})'
                    break
            
            except requests.Timeout:
                print(f"[AI] 타임아웃 ({model})")
                last_error = '해석 생성 시간 초과. 잠시 후 다시 시도해주세요.'
                break
            except Exception as e:
                print(f"[AI] 예외: {str(e)[:100]}")
                last_error = str(e)[:200]
                break
    
    print(f"[AI] 모든 모델 실패: {last_error}")
    return {'success': False, 'error': last_error or 'AI 해석 생성 실패', 'interpretation': None}


def get_ai_interpretation(saju_data):
    """종합 사주 해석"""
    prompt = build_saju_prompt(saju_data)
    return _call_gemini(prompt)


def get_category_interpretation(saju_data, category):
    """카테고리별 상세 해석"""
    category_prompts = {
        'love': '연애운과 궁합, 결혼 시기에 대해 집중적으로 상세 분석해주세요. 도화살, 합충 관계를 중심으로.',
        'money': '재물운과 투자 적성에 대해 집중 분석해주세요. 재성(편재/정재), 식상의 역할을 중심으로.',
        'career': '직업운과 적성, 승진/이직 시기에 대해 분석해주세요. 관성, 인성, 식상을 중심으로.',
        'health': '건강 주의사항을 오행 불균형 관점에서 상세 분석해주세요. 약한 오행과 관련된 장기를 중심으로.',
        'yearly': f'{saju_data["current_year"]["year"]}년 올해 운세를 월별로 상세히 분석해주세요. 세운과 원국의 상호작용을 중심으로.',
    }
    
    if category not in category_prompts:
        return {'success': False, 'error': '잘못된 카테고리', 'interpretation': None}
    
    prompt = build_saju_prompt(saju_data)
    extra = f"\n\n[특별 요청]\n{category_prompts[category]}\n3000자 이상 상세하게 작성해주세요."
    
    return _call_gemini(prompt, extra, max_tokens=8192, timeout=90)
