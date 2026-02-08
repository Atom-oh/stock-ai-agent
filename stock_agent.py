#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
주식 정보 AI Agent - 백엔드 도구 모듈

이 모듈은 AI 에이전트가 사용하는 도구(Tool)들을 정의합니다.
각 도구는 @tool 데코레이터로 정의되며, AI가 자동으로 호출할 수 있습니다.

제공 기능:
- 실시간 주가 조회 (한국/미국 주식)
- 기술적 분석 (이동평균, RSI, MACD, 볼린저밴드)
- 기본적 분석 (밸류에이션, 수익성, 재무건전성)
- 기관/내부자 보유 현황
- 동종업계 비교 분석
- 거시경제 지표
- 뉴스 감성 분석 (NLP 기반)

사용 기술:
- yfinance: 야후 파이낸스 API (주가, 재무 데이터)
- feedparser: RSS 뉴스 피드 파싱
- Strands Agent SDK: AI 에이전트 프레임워크
- AWS Bedrock: Claude 3.5 Sonnet 모델
"""

# =============================================================================
# 라이브러리 임포트
# =============================================================================
import sys                        # 시스템 설정 (인코딩)
import os                         # 운영체제 인터페이스
import yfinance as yf             # 야후 파이낸스 API
import pandas as pd               # 데이터 처리
import feedparser                 # RSS 피드 파싱
from datetime import datetime, timedelta  # 날짜/시간 처리
from strands import Agent, tool   # AI 에이전트 및 도구 데코레이터
from strands.models import BedrockModel   # AWS Bedrock 모델 래퍼

# =============================================================================
# UTF-8 인코딩 설정
# Windows 환경에서 한글 출력을 위한 설정
# =============================================================================
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stdin.encoding != 'utf-8':
    sys.stdin.reconfigure(encoding='utf-8')


# =============================================================================
# 회사명 → 티커 심볼 매핑 테이블
# 사용자가 입력한 회사명을 yfinance가 인식할 수 있는 티커로 변환
#
# 한국 주식: 6자리 코드 + .KS (예: 005930.KS = 삼성전자)
# 미국 주식: 영문 티커 심볼 (예: AAPL = 애플)
# =============================================================================
TICKER_MAP = {
    # 미국 주식 (영문/한글 모두 지원)
    "amazon": "AMZN", "아마존": "AMZN",
    "apple": "AAPL", "애플": "AAPL",
    "tesla": "TSLA", "테슬라": "TSLA",
    "google": "GOOGL", "구글": "GOOGL",
    "microsoft": "MSFT", "마이크로소프트": "MSFT",
    "meta": "META", "메타": "META",
    "nvidia": "NVDA", "엔비디아": "NVDA",
    # 한국 주식 (종목코드.KS 형식)
    "삼성전자": "005930.KS",
    "sk하이닉스": "000660.KS", "SK하이닉스": "000660.KS", "하이닉스": "000660.KS",
    "네이버": "035420.KS",
    "카카오": "035720.KS",
    "현대차": "005380.KS", "현대자동차": "005380.KS",
    "lg전자": "066570.KS", "LG전자": "066570.KS",
    "포스코": "005490.KS"
}


def get_ticker(company_name: str) -> str:
    """회사명을 티커 심볼로 변환
    
    Args:
        company_name: 회사명 (예: "삼성전자", "SK 하이닉스", "Amazon")
    
    Returns:
        티커 심볼 (예: "005930.KS", "AMZN")
    
    처리 로직:
    1. 공백 제거 ("SK 하이닉스" → "SK하이닉스")
    2. TICKER_MAP에서 검색
    3. 없으면 6자리 숫자는 .KS 추가
    4. 그 외는 대문자로 변환
    """
    # 공백 제거
    cleaned_name = company_name.replace(" ", "")
    # 영문은 소문자로, 한글은 그대로
    search_key = cleaned_name.lower() if cleaned_name.isascii() else cleaned_name
    # 티커 매핑에서 검색
    ticker = TICKER_MAP.get(search_key)
    
    if not ticker:
        # 6자리 숫자는 한국 주식 코드로 간주
        if company_name.isdigit() and len(company_name) == 6:
            ticker = f"{company_name}.KS"
        else:
            # 그 외는 대문자로 변환 (직접 티커 입력 가능)
            ticker = company_name.upper()
    
    return ticker


# =============================================================================
# 도구 1: 기술적 분석 (Technical Analysis)
# =============================================================================
@tool
def analyze_stock_trend(company_name: str, period: str = "3mo") -> dict:
    """주가 추이를 분석하여 투자 판단에 도움이 되는 데이터를 제공합니다.

    기술적 분석 지표:
    - 이동평균선 (MA5, MA20, MA60)
    - RSI (상대강도지수) - 과매수/과매도 판단
    - MACD (추세 전환 신호)
    - 볼린저밴드 (변동성 범위)
    - 골든크로스/데드크로스 (매수/매도 신호)

    Args:
        company_name: 회사명을 정확히 입력하세요.
                     예시: "삼성전자", "005930", "Amazon"
                     주의: 영어로 번역하지 말고 사용자가 입력한 그대로 전달하세요.
        period: 분석 기간 ("1mo", "3mo", "6mo", "1y") 기본값 3개월

    Returns:
        주가 분석 데이터 (이동평균, RSI, 변동성 등)
    """
    # 회사명을 티커 심볼로 변환
    ticker = get_ticker(company_name)

    # yfinance API로 주가 데이터 조회
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)  # OHLCV 데이터
    except Exception as e:
        return {"error": f"데이터 조회 실패: {str(e)}"}
    
    # 데이터가 없으면 에러 반환
    if df.empty:
        return {"error": f"{company_name}의 데이터를 가져올 수 없습니다. 한국 주식의 경우 6자리 종목코드를 입력해주세요."}
    
    # 현재가
    current_price = df['Close'].iloc[-1]
    
    # 이동평균선 계산 (5일, 20일, 60일)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    ma5 = df['MA5'].iloc[-1] if len(df) >= 5 else None
    ma20 = df['MA20'].iloc[-1] if len(df) >= 20 else None
    ma60 = df['MA60'].iloc[-1] if len(df) >= 60 else None
    
    # RSI 계산 (14일) - 0으로 나누기 방지
    delta = df['Close'].diff()  # 전일 대비 변화량
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()  # 상승분 평균
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()  # 하락분 평균
    
    # loss가 0인 경우 처리 (0으로 나누기 방지)
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1] if len(df) >= 14 and not pd.isna(rsi.iloc[-1]) else None
    
    # 변동성 계산 (최근 30일 고가-저가 범위)
    recent_30d = df.tail(30)
    if len(recent_30d) > 0 and recent_30d['Low'].min() > 0:
        volatility = ((recent_30d['High'].max() - recent_30d['Low'].min()) / recent_30d['Low'].min()) * 100
    else:
        volatility = 0
    
    # 거래량 추이 (최근 거래량 vs 20일 평균)
    avg_volume = df['Volume'].tail(20).mean()
    recent_volume = df['Volume'].iloc[-1]
    volume_ratio = (recent_volume / avg_volume) * 100 if avg_volume > 0 else 0
    
    # 기간 수익률 (시작가 대비 현재가) - ZeroDivision 방지
    start_price = df['Close'].iloc[0]
    period_return = ((current_price - start_price) / start_price) * 100 if start_price > 0 else 0
    
    # MACD (Moving Average Convergence Divergence) - 추세 전환 신호
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()  # 12일 지수이동평균
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()  # 26일 지수이동평균
    macd = exp12 - exp26  # MACD 선
    signal = macd.ewm(span=9, adjust=False).mean()  # 시그널 선
    macd_histogram = macd - signal  # 히스토그램 (MACD - Signal)
    
    # 볼린저 밴드 (20일 기준, 2 표준편차)
    bb_middle = df['Close'].rolling(window=20).mean()  # 중심선 (20일 이동평균)
    bb_std = df['Close'].rolling(window=20).std()  # 표준편차
    bb_upper = bb_middle + (bb_std * 2)  # 상단 밴드
    bb_lower = bb_middle - (bb_std * 2)  # 하단 밴드
    
    # 현재가의 볼린저 밴드 위치 (%) - 0%=하단, 100%=상단 - ZeroDivision 방지
    if len(df) >= 20:
        bb_width = bb_upper.iloc[-1] - bb_lower.iloc[-1]
        bb_position = ((current_price - bb_lower.iloc[-1]) / bb_width) * 100 if bb_width > 0 else 50
    else:
        bb_position = None
    
    # 골든크로스/데드크로스 확인 (MA5와 MA20 교차)
    cross_signal = None
    if ma5 and ma20 and len(df) >= 21:
        prev_ma5 = df['MA5'].iloc[-2]
        prev_ma20 = df['MA20'].iloc[-2]
        # 골든크로스: 단기 이평선이 장기 이평선을 상향 돌파 (매수 신호)
        if prev_ma5 <= prev_ma20 and ma5 > ma20:
            cross_signal = "골든크로스"
        # 데드크로스: 단기 이평선이 장기 이평선을 하향 돌파 (매도 신호)
        elif prev_ma5 >= prev_ma20 and ma5 < ma20:
            cross_signal = "데드크로스"
    
    # 분석 결과 반환
    return {
        "company": company_name,
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "period": period,
        "period_return": round(period_return, 2),  # 기간 수익률
        "ma5": round(ma5, 2) if ma5 else None,  # 5일 이동평균
        "ma20": round(ma20, 2) if ma20 else None,  # 20일 이동평균
        "ma60": round(ma60, 2) if ma60 else None,  # 60일 이동평균
        "rsi": round(current_rsi, 2) if current_rsi else None,  # RSI (과매수/과매도)
        "macd": round(macd.iloc[-1], 2) if len(df) >= 26 else None,  # MACD 선
        "macd_signal": round(signal.iloc[-1], 2) if len(df) >= 26 else None,  # 시그널 선
        "macd_histogram": round(macd_histogram.iloc[-1], 2) if len(df) >= 26 else None,  # 히스토그램
        "bb_position": round(bb_position, 2) if bb_position else None,  # 볼린저밴드 위치 (%)
        "cross_signal": cross_signal,  # 골든크로스/데드크로스
        "volatility": round(volatility, 2),  # 변동성
        "volume_ratio": round(volume_ratio, 2),  # 거래량 비율
        "highest": round(df['High'].max(), 2),  # 기간 최고가
        "lowest": round(df['Low'].min(), 2)  # 기간 최저가
    }


# =============================================================================
# 뉴스 감성 분석 헬퍼 함수 (NLP 기반)
# =============================================================================
def analyze_sentiment(text: str) -> dict:
    """뉴스 제목의 감성을 분석하여 점수화합니다.

    키워드 기반 감성 분석:
    - 긍정 키워드: surge, soar, beat, rise, gain, rally, upgrade 등
    - 부정 키워드: crash, plunge, fall, drop, decline, downgrade 등
    - 각 키워드에 가중치를 부여하여 점수 계산

    Args:
        text: 분석할 텍스트 (뉴스 제목)

    Returns:
        감성 점수 (-100 ~ +100), 감성 라벨, 키워드
    """
    text_lower = text.lower()

    # -------------------------------------------------------------------------
    # 긍정 키워드 사전 (가중치 포함)
    # 강한 긍정: +15, 중간 긍정: +10, 약한 긍정: +5
    # -------------------------------------------------------------------------
    positive_keywords = {
        # 강한 긍정 (+15) - 급등, 신기록 등
        "surge": 15, "soar": 15, "skyrocket": 15, "breakthrough": 15, "record high": 15,
        "beat": 12, "beats": 12, "exceed": 12, "exceeds": 12, "outperform": 12,
        # 중간 긍정 (+10) - 상승, 성장 등
        "rise": 10, "rises": 10, "gain": 10, "gains": 10, "jump": 10, "jumps": 10,
        "rally": 10, "rallies": 10, "climb": 10, "climbs": 10, "boost": 10,
        "upgrade": 10, "upgrades": 10, "bullish": 10, "growth": 10, "profit": 10,
        # 약한 긍정 (+5) - 일반 긍정 표현
        "up": 5, "higher": 5, "positive": 5, "strong": 5, "buy": 5,
        "recover": 5, "recovery": 5, "improve": 5, "expansion": 5, "deal": 5,
        "partnership": 5, "innovation": 5, "launch": 5, "success": 5, "win": 5
    }

    # -------------------------------------------------------------------------
    # 부정 키워드 사전 (가중치 포함)
    # 강한 부정: -15, 중간 부정: -10, 약한 부정: -5
    # -------------------------------------------------------------------------
    negative_keywords = {
        # 강한 부정 (-15) - 폭락, 스캔들 등
        "crash": -15, "plunge": -15, "collapse": -15, "scandal": -15, "fraud": -15,
        "bankruptcy": -15, "lawsuit": -15, "investigation": -15,
        # 중간 부정 (-10) - 하락, 손실 등
        "fall": -10, "falls": -10, "drop": -10, "drops": -10, "decline": -10,
        "declines": -10, "tumble": -10, "sink": -10, "sinks": -10, "slump": -10,
        "downgrade": -10, "downgrades": -10, "bearish": -10, "loss": -10, "losses": -10,
        # 약한 부정 (-5) - 일반 부정 표현
        "down": -5, "lower": -5, "negative": -5, "weak": -5, "sell": -5,
        "concern": -5, "concerns": -5, "risk": -5, "risks": -5, "warning": -5,
        "cut": -5, "cuts": -5, "layoff": -5, "layoffs": -5, "miss": -5, "misses": -5
    }

    score = 0
    found_positive = []
    found_negative = []

    # 키워드 매칭 및 점수 계산
    for keyword, weight in positive_keywords.items():
        if keyword in text_lower:
            score += weight
            found_positive.append(keyword)

    for keyword, weight in negative_keywords.items():
        if keyword in text_lower:
            score += weight  # weight는 이미 음수
            found_negative.append(keyword)

    # 점수 범위 제한 (-100 ~ +100)
    score = max(-100, min(100, score))

    # 감성 라벨 결정
    if score >= 20:
        label = "매우 긍정"
    elif score >= 5:
        label = "긍정"
    elif score <= -20:
        label = "매우 부정"
    elif score <= -5:
        label = "부정"
    else:
        label = "중립"

    return {
        "score": score,
        "label": label,
        "positive_keywords": found_positive,
        "negative_keywords": found_negative
    }


# =============================================================================
# 도구 2: 뉴스 감성 분석 (News Sentiment Analysis)
# =============================================================================
@tool
def analyze_company_news(company_name: str) -> dict:
    """회사 관련 최근 뉴스를 수집하고 NLP 기반 감성을 분석합니다.

    Google News RSS 피드를 통해 최근 뉴스를 수집하고,
    키워드 기반 감성 분석으로 각 기사의 긍정/부정을 점수화합니다.

    Args:
        company_name: 회사명을 정확히 입력하세요.
                     예시: "삼성전자", "Amazon"
                     주의: 영어로 번역하지 말고 사용자가 입력한 그대로 전달하세요.

    Returns:
        최근 뉴스 목록, 개별 감성 점수, 종합 감성 점수
    """
    from urllib.parse import quote  # URL 인코딩용

    # 영문 회사명 매핑 (Google News 검색용)
    english_name_map = {
        "삼성전자": "Samsung Electronics", "삼성 전자": "Samsung Electronics",
        "sk하이닉스": "SK Hynix", "하이닉스": "SK Hynix", "sk 하이닉스": "SK Hynix",
        "네이버": "Naver",
        "카카오": "Kakao",
        "현대차": "Hyundai Motor", "현대자동차": "Hyundai Motor", "현대 차": "Hyundai Motor",
        "lg전자": "LG Electronics", "lg 전자": "LG Electronics",
        "포스코": "POSCO",
        "아마존": "Amazon",
        "애플": "Apple",
        "테슬라": "Tesla",
        "구글": "Google",
        "마이크로소프트": "Microsoft",
        "메타": "Meta",
        "엔비디아": "Nvidia"
    }

    search_key = company_name.replace(" ", "")
    search_name = english_name_map.get(search_key, company_name)

    encoded_query = quote(f"{search_name} stock")
    news_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        feed = feedparser.parse(news_url)

        if not feed.entries:
            return {
                "company": company_name,
                "news_count": 0,
                "news": [],
                "overall_sentiment": {"score": 0, "label": "중립"},
                "error": "뉴스를 찾을 수 없습니다."
            }

        # 최근 5개 뉴스 수집 및 감성 분석
        news_list = []
        total_score = 0

        for entry in feed.entries[:5]:
            sentiment = analyze_sentiment(entry.title)
            total_score += sentiment["score"]

            news_list.append({
                "title": entry.title,
                "published": entry.get('published', 'N/A'),
                "link": entry.link,
                "sentiment_score": sentiment["score"],
                "sentiment_label": sentiment["label"],
                "positive_keywords": sentiment["positive_keywords"],
                "negative_keywords": sentiment["negative_keywords"]
            })

        # 종합 감성 점수 계산 (평균)
        avg_score = total_score / len(news_list) if news_list else 0

        # 종합 감성 라벨
        if avg_score >= 15:
            overall_label = "매우 긍정"
        elif avg_score >= 5:
            overall_label = "긍정"
        elif avg_score <= -15:
            overall_label = "매우 부정"
        elif avg_score <= -5:
            overall_label = "부정"
        else:
            overall_label = "중립"

        # 긍정/부정 뉴스 개수
        positive_count = sum(1 for n in news_list if n["sentiment_score"] > 0)
        negative_count = sum(1 for n in news_list if n["sentiment_score"] < 0)
        neutral_count = len(news_list) - positive_count - negative_count

        return {
            "company": company_name,
            "search_name": search_name,
            "news_count": len(news_list),
            "news": news_list,
            "overall_sentiment": {
                "score": round(avg_score, 1),
                "label": overall_label,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count
            }
        }

    except Exception as e:
        return {
            "company": company_name,
            "error": f"뉴스 수집 중 오류 발생: {str(e)}"
        }


# =============================================================================
# 도구 3: 현재가 조회 (Current Price)
# =============================================================================
@tool
def get_stock_price(company_name: str) -> dict:
    """주식 현재가 및 변동 정보를 조회합니다.

    현재가, 전일 종가, 변동률을 반환합니다.

    Args:
        company_name: 회사명을 정확히 입력하세요.
                     예시: "삼성전자", "네이버", "Amazon", "Apple"
                     주의: 영어로 번역하지 말고 사용자가 입력한 그대로 전달하세요.

    Returns:
        주가 정보를 담은 딕셔너리 (current_price, previous_price, change_percent)
    """
    # 회사명을 티커 심볼로 변환
    ticker = get_ticker(company_name)

    # yfinance로 최근 2일 주가 데이터 조회 (현재가와 전일가 비교용)
    try:
        stock = yf.Ticker(ticker)
        info = stock.history(period="2d")
    except Exception as e:
        return {"error": f"데이터 조회 실패: {str(e)}"}
    
    # 데이터가 없으면 에러 반환
    if info.empty:
        return {"error": f"{company_name}의 주가 정보를 찾을 수 없습니다. 한국 주식의 경우 6자리 종목코드(예: 051910)를 입력하거나, 주요 기업명(삼성전자, 네이버, 카카오 등)을 입력해주세요."}
    
    # 현재가 (가장 최근 종가)
    current_price = info['Close'].iloc[-1]
    # 전일 종가
    previous_price = info['Close'].iloc[-2] if len(info) > 1 else current_price
    
    # 변동률 계산 (0으로 나누기 방지)
    if previous_price > 0:
        change_percent = ((current_price - previous_price) / previous_price) * 100
    else:
        change_percent = 0
    
    return {
        "company": company_name,
        "ticker": ticker,
        "current_price": round(current_price, 2),  # 현재가
        "previous_price": round(previous_price, 2),  # 전일 종가
        "change_percent": round(change_percent, 2)  # 변동률 (%)
    }


# =============================================================================
# 도구 4: 기본적 분석 (Fundamental Analysis)
# =============================================================================
@tool
def get_fundamental_analysis(company_name: str) -> dict:
    """기업의 기본적 분석(펀더멘털) 데이터를 조회합니다.

    포함 지표:
    - 밸류에이션: P/E, P/B, PEG, PSR
    - 수익성: ROE, ROA, 영업이익률, 순이익률
    - 재무건전성: 부채비율, 유동비율, 당좌비율
    - 성장성: 매출성장률, 이익성장률

    Args:
        company_name: 회사명을 정확히 입력하세요.
                     예시: "삼성전자", "Amazon", "Apple"
                     주의: 영어로 번역하지 말고 사용자가 입력한 그대로 전달하세요.

    Returns:
        밸류에이션, 수익성, 재무건전성, 성장성 지표
    """
    ticker = get_ticker(company_name)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
    except Exception as e:
        return {"error": f"데이터 조회 실패: {str(e)}"}

    if not info:
        return {"error": f"{company_name}의 재무 정보를 찾을 수 없습니다."}

    # 안전하게 값 가져오기 (None 처리)
    def safe_get(key, multiplier=1, decimal=2):
        value = info.get(key)
        if value is not None:
            return round(value * multiplier, decimal)
        return None

    # 밸류에이션 지표
    valuation = {
        "pe_ratio": safe_get('trailingPE'),  # P/E (주가수익비율)
        "forward_pe": safe_get('forwardPE'),  # 예상 P/E
        "pb_ratio": safe_get('priceToBook'),  # P/B (주가순자산비율)
        "peg_ratio": safe_get('pegRatio'),  # PEG (주가수익성장비율)
        "ps_ratio": safe_get('priceToSalesTrailing12Months'),  # PSR (주가매출비율)
    }

    # 수익성 지표
    profitability = {
        "roe": safe_get('returnOnEquity', 100),  # ROE (자기자본이익률) %
        "roa": safe_get('returnOnAssets', 100),  # ROA (총자산이익률) %
        "operating_margin": safe_get('operatingMargins', 100),  # 영업이익률 %
        "profit_margin": safe_get('profitMargins', 100),  # 순이익률 %
        "gross_margin": safe_get('grossMargins', 100),  # 매출총이익률 %
    }

    # 재무건전성 지표
    financial_health = {
        "debt_to_equity": safe_get('debtToEquity'),  # 부채비율
        "current_ratio": safe_get('currentRatio'),  # 유동비율
        "quick_ratio": safe_get('quickRatio'),  # 당좌비율
    }

    # 성장성 지표
    growth = {
        "revenue_growth": safe_get('revenueGrowth', 100),  # 매출 성장률 %
        "earnings_growth": safe_get('earningsGrowth', 100),  # 이익 성장률 %
    }

    # 기타 정보
    other = {
        "market_cap": info.get('marketCap'),  # 시가총액
        "enterprise_value": info.get('enterpriseValue'),  # 기업가치
        "dividend_yield": safe_get('dividendYield', 100),  # 배당수익률 %
        "dividend_rate": info.get('dividendRate'),  # 배당금
        "beta": safe_get('beta'),  # 베타 (시장 대비 변동성)
        "fifty_two_week_high": safe_get('fiftyTwoWeekHigh'),  # 52주 최고가
        "fifty_two_week_low": safe_get('fiftyTwoWeekLow'),  # 52주 최저가
        "eps": safe_get('trailingEps'),  # 주당순이익
        "book_value": safe_get('bookValue'),  # 주당순자산
    }

    return {
        "company": company_name,
        "ticker": ticker,
        "valuation": valuation,
        "profitability": profitability,
        "financial_health": financial_health,
        "growth": growth,
        "other": other
    }


# =============================================================================
# 도구 5: 기관/내부자 보유 현황 (Institutional Holdings)
# =============================================================================
@tool
def get_institutional_holders(company_name: str) -> dict:
    """기관 및 주요 투자자 보유 현황을 조회합니다.

    포함 정보:
    - 기관투자자 보유비율
    - 내부자(경영진) 보유비율
    - 주요 기관투자자 목록 (상위 5개)
    - 주요 펀드 보유 목록 (상위 5개)

    Args:
        company_name: 회사명을 정확히 입력하세요.
                     예시: "삼성전자", "Amazon", "Apple"
                     주의: 영어로 번역하지 말고 사용자가 입력한 그대로 전달하세요.

    Returns:
        기관투자자 보유비율, 주요 주주 목록
    """
    ticker = get_ticker(company_name)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
    except Exception as e:
        return {"error": f"데이터 조회 실패: {str(e)}"}

    # 기관/내부자 보유비율
    institutional_percent = info.get('heldPercentInstitutions')
    insider_percent = info.get('heldPercentInsiders')

    # 주요 기관투자자 목록
    top_institutions = []
    try:
        holders = stock.institutional_holders
        if holders is not None and not holders.empty:
            for _, row in holders.head(5).iterrows():
                top_institutions.append({
                    "holder": row.get('Holder', 'N/A'),
                    "shares": int(row.get('Shares', 0)) if pd.notna(row.get('Shares')) else 0,
                    "value": int(row.get('Value', 0)) if pd.notna(row.get('Value')) else 0,
                    "percent": round(row.get('pctHeld', 0) * 100, 2) if pd.notna(row.get('pctHeld')) else None
                })
    except Exception:
        pass  # 기관투자자 데이터가 없는 경우

    # 주요 펀드 보유 목록
    top_funds = []
    try:
        funds = stock.mutualfund_holders
        if funds is not None and not funds.empty:
            for _, row in funds.head(5).iterrows():
                top_funds.append({
                    "holder": row.get('Holder', 'N/A'),
                    "shares": int(row.get('Shares', 0)) if pd.notna(row.get('Shares')) else 0,
                    "value": int(row.get('Value', 0)) if pd.notna(row.get('Value')) else 0,
                    "percent": round(row.get('pctHeld', 0) * 100, 2) if pd.notna(row.get('pctHeld')) else None
                })
    except Exception:
        pass  # 펀드 데이터가 없는 경우

    return {
        "company": company_name,
        "ticker": ticker,
        "institutional_percent": round(institutional_percent * 100, 2) if institutional_percent else None,
        "insider_percent": round(insider_percent * 100, 2) if insider_percent else None,
        "top_institutions": top_institutions,
        "top_funds": top_funds,
        "float_shares": info.get('floatShares'),  # 유통주식수
        "shares_outstanding": info.get('sharesOutstanding'),  # 발행주식수
    }


# =============================================================================
# 도구 6: 동종업계 비교 분석 (Peer Comparison)
# =============================================================================
@tool
def get_peer_comparison(company_name: str) -> dict:
    """동종업계 경쟁사와 주요 지표를 비교 분석합니다.

    비교 지표:
    - 밸류에이션: P/E, P/B, PSR
    - 수익성: ROE, 순이익률
    - 성장성: 매출성장률

    상대 평가:
    - 업종 평균 대비 저평가/고평가 판단
    - 업종 평균 대비 수익성/성장성 평가

    Args:
        company_name: 회사명을 정확히 입력하세요.
                     예시: "삼성전자", "Amazon", "Apple"
                     주의: 영어로 번역하지 말고 사용자가 입력한 그대로 전달하세요.

    Returns:
        동종업계 비교 데이터 (섹터, 업종, 경쟁사 지표 비교)
    """
    ticker = get_ticker(company_name)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
    except Exception as e:
        return {"error": f"데이터 조회 실패: {str(e)}"}

    # 섹터/업종 정보
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')

    # 업종별 대표 경쟁사 매핑
    industry_peers = {
        # 반도체
        "Semiconductors": ["NVDA", "AMD", "INTC", "TSM", "AVGO"],
        "Semiconductor Equipment & Materials": ["ASML", "AMAT", "LRCX", "KLAC"],
        # 테크
        "Consumer Electronics": ["AAPL", "005930.KS", "SONY", "066570.KS"],
        "Internet Content & Information": ["GOOGL", "META", "035420.KS", "035720.KS"],
        "Software - Infrastructure": ["MSFT", "ORCL", "CRM", "NOW"],
        # 자동차
        "Auto Manufacturers": ["TSLA", "TM", "F", "GM", "005380.KS"],
        # 이커머스/리테일
        "Internet Retail": ["AMZN", "BABA", "JD", "EBAY"],
        # 기타 테크
        "Information Technology Services": ["IBM", "ACN", "INFY"],
    }

    # 현재 회사의 업종에 맞는 경쟁사 선택
    peer_tickers = industry_peers.get(industry, [])

    # 경쟁사가 없으면 같은 섹터의 대표 기업들 사용
    if not peer_tickers:
        sector_defaults = {
            "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE"],
            "Communication Services": ["GOOGL", "META", "NFLX", "DIS"],
            "Financial Services": ["JPM", "BAC", "GS", "MS"],
            "Healthcare": ["JNJ", "UNH", "PFE", "ABBV"],
        }
        peer_tickers = sector_defaults.get(sector, [])

    # 현재 회사가 리스트에 있으면 제거
    peer_tickers = [t for t in peer_tickers if t != ticker][:4]  # 최대 4개 경쟁사

    # 현재 회사 데이터 수집
    def safe_get(data, key, multiplier=1, decimal=2):
        value = data.get(key)
        if value is not None:
            return round(value * multiplier, decimal)
        return None

    company_data = {
        "ticker": ticker,
        "name": company_name,
        "pe_ratio": safe_get(info, 'trailingPE'),
        "pb_ratio": safe_get(info, 'priceToBook'),
        "ps_ratio": safe_get(info, 'priceToSalesTrailing12Months'),
        "roe": safe_get(info, 'returnOnEquity', 100),
        "profit_margin": safe_get(info, 'profitMargins', 100),
        "revenue_growth": safe_get(info, 'revenueGrowth', 100),
        "market_cap": info.get('marketCap'),
        "beta": safe_get(info, 'beta')
    }

    # 경쟁사 데이터 수집
    peers_data = []
    for peer_ticker in peer_tickers:
        try:
            peer_stock = yf.Ticker(peer_ticker)
            peer_info = peer_stock.info
            peer_name = peer_info.get('shortName', peer_ticker)

            peers_data.append({
                "ticker": peer_ticker,
                "name": peer_name,
                "pe_ratio": safe_get(peer_info, 'trailingPE'),
                "pb_ratio": safe_get(peer_info, 'priceToBook'),
                "ps_ratio": safe_get(peer_info, 'priceToSalesTrailing12Months'),
                "roe": safe_get(peer_info, 'returnOnEquity', 100),
                "profit_margin": safe_get(peer_info, 'profitMargins', 100),
                "revenue_growth": safe_get(peer_info, 'revenueGrowth', 100),
                "market_cap": peer_info.get('marketCap'),
                "beta": safe_get(peer_info, 'beta')
            })
        except Exception:
            continue

    # 업종 평균 계산
    def calc_average(key):
        values = [p[key] for p in peers_data if p.get(key) is not None]
        if company_data.get(key) is not None:
            values.append(company_data[key])
        return round(sum(values) / len(values), 2) if values else None

    industry_avg = {
        "pe_ratio": calc_average("pe_ratio"),
        "pb_ratio": calc_average("pb_ratio"),
        "ps_ratio": calc_average("ps_ratio"),
        "roe": calc_average("roe"),
        "profit_margin": calc_average("profit_margin"),
        "revenue_growth": calc_average("revenue_growth")
    }

    # 상대적 위치 평가
    def evaluate_position(company_val, avg_val, metric_type):
        if company_val is None or avg_val is None:
            return "N/A"
        diff_pct = ((company_val - avg_val) / avg_val) * 100 if avg_val != 0 else 0

        # P/E, P/B, P/S는 낮을수록 좋음
        if metric_type in ["pe_ratio", "pb_ratio", "ps_ratio"]:
            if diff_pct <= -20:
                return "매우 저평가"
            elif diff_pct <= -5:
                return "저평가"
            elif diff_pct >= 20:
                return "매우 고평가"
            elif diff_pct >= 5:
                return "고평가"
            else:
                return "적정"
        # ROE, profit_margin, revenue_growth는 높을수록 좋음
        else:
            if diff_pct >= 20:
                return "업종 상위"
            elif diff_pct >= 5:
                return "업종 평균 이상"
            elif diff_pct <= -20:
                return "업종 하위"
            elif diff_pct <= -5:
                return "업종 평균 이하"
            else:
                return "업종 평균"

    relative_position = {
        "pe_ratio": evaluate_position(company_data["pe_ratio"], industry_avg["pe_ratio"], "pe_ratio"),
        "pb_ratio": evaluate_position(company_data["pb_ratio"], industry_avg["pb_ratio"], "pb_ratio"),
        "ps_ratio": evaluate_position(company_data["ps_ratio"], industry_avg["ps_ratio"], "ps_ratio"),
        "roe": evaluate_position(company_data["roe"], industry_avg["roe"], "roe"),
        "profit_margin": evaluate_position(company_data["profit_margin"], industry_avg["profit_margin"], "profit_margin"),
        "revenue_growth": evaluate_position(company_data["revenue_growth"], industry_avg["revenue_growth"], "revenue_growth")
    }

    return {
        "company": company_name,
        "ticker": ticker,
        "sector": sector,
        "industry": industry,
        "company_metrics": company_data,
        "peers": peers_data,
        "industry_average": industry_avg,
        "relative_position": relative_position,
        "peer_count": len(peers_data)
    }


# =============================================================================
# 도구 7: 거시경제 지표 (Macro Indicators)
# =============================================================================
@tool
def get_macro_indicators() -> dict:
    """거시경제 지표를 조회합니다. 시장 전반의 상황을 파악하는데 사용합니다.

    포함 지표:
    - 주요 지수: S&P 500, NASDAQ, Dow Jones, KOSPI, KOSDAQ 등
    - 변동성: VIX (공포지수)
    - 채권/금리: 미국 10년물 국채 금리
    - 환율: USD/KRW, EUR/USD, USD/JPY, 달러인덱스
    - 원자재: 금, 원유, 은, 천연가스

    Returns:
        주요 지수, 변동성, 금리, 환율, 원자재 정보
    """
    import warnings
    warnings.filterwarnings('ignore')  # yfinance 경고 메시지 무시

    result = {
        "indices": {},      # 주요 지수
        "volatility": {},   # 변동성 지표
        "bonds": {},        # 채권/금리
        "currencies": {},   # 환율
        "commodities": {},  # 원자재
        "market_sentiment": None  # 시장 심리
    }

    # 주요 지수 티커
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "Nikkei 225": "^N225",
        "Shanghai": "000001.SS"
    }

    # 주요 지수 조회
    for name, ticker in indices.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty and len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change_pct = ((current - prev) / prev) * 100 if prev > 0 else 0
                result["indices"][name] = {
                    "price": round(current, 2),
                    "change_percent": round(change_pct, 2)
                }
        except Exception:
            pass

    # VIX (공포지수)
    try:
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        if not vix_hist.empty:
            current_vix = vix_hist['Close'].iloc[-1]
            result["volatility"]["VIX"] = {
                "value": round(current_vix, 2),
                "interpretation": "극심한 공포" if current_vix > 30 else ("공포" if current_vix > 20 else ("중립" if current_vix > 15 else "안정"))
            }
    except Exception:
        pass

    # 미국 국채 금리
    bonds = {
        "US 10Y Treasury": "^TNX",  # 10년물
        "US 2Y Treasury": "^IRX",   # 2년물 (3개월 단기)
    }

    for name, ticker in bonds.items():
        try:
            bond = yf.Ticker(ticker)
            bond_hist = bond.history(period="5d")
            if not bond_hist.empty:
                current = bond_hist['Close'].iloc[-1]
                result["bonds"][name] = {
                    "yield": round(current, 3)
                }
        except Exception:
            pass

    # 환율
    currencies = {
        "USD/KRW": "KRW=X",
        "USD Index (DXY)": "DX-Y.NYB",
        "EUR/USD": "EURUSD=X",
        "USD/JPY": "JPY=X"
    }

    for name, ticker in currencies.items():
        try:
            fx = yf.Ticker(ticker)
            fx_hist = fx.history(period="5d")
            if not fx_hist.empty and len(fx_hist) >= 2:
                current = fx_hist['Close'].iloc[-1]
                prev = fx_hist['Close'].iloc[-2]
                change_pct = ((current - prev) / prev) * 100 if prev > 0 else 0
                result["currencies"][name] = {
                    "rate": round(current, 2),
                    "change_percent": round(change_pct, 2)
                }
        except Exception:
            pass

    # 원자재
    commodities = {
        "Gold": "GC=F",
        "Crude Oil (WTI)": "CL=F",
        "Silver": "SI=F",
        "Natural Gas": "NG=F"
    }

    for name, ticker in commodities.items():
        try:
            comm = yf.Ticker(ticker)
            comm_hist = comm.history(period="5d")
            if not comm_hist.empty and len(comm_hist) >= 2:
                current = comm_hist['Close'].iloc[-1]
                prev = comm_hist['Close'].iloc[-2]
                change_pct = ((current - prev) / prev) * 100 if prev > 0 else 0
                result["commodities"][name] = {
                    "price": round(current, 2),
                    "change_percent": round(change_pct, 2)
                }
        except Exception:
            pass

    # 시장 심리 판단 (VIX 기반)
    vix_data = result["volatility"].get("VIX", {})
    if vix_data:
        vix_value = vix_data.get("value", 20)
        sp500_change = result["indices"].get("S&P 500", {}).get("change_percent", 0)

        if vix_value > 25 and sp500_change < -1:
            result["market_sentiment"] = "극도의 공포 (매수 기회 가능)"
        elif vix_value > 20:
            result["market_sentiment"] = "불안 (신중한 접근 필요)"
        elif vix_value < 15 and sp500_change > 0:
            result["market_sentiment"] = "낙관 (과열 주의)"
        else:
            result["market_sentiment"] = "중립"

    return result


# =============================================================================
# 메인 함수 - CLI 모드 실행용
# (Streamlit 앱에서는 이 함수를 사용하지 않음)
# =============================================================================
def main():
    """메인 함수 - Agent 초기화 및 대화 루프

    CLI(Command Line Interface) 모드로 직접 실행할 때 사용됩니다.
    터미널에서 회사명을 입력하면 AI가 분석 결과를 출력합니다.
    """

    # AWS Bedrock Claude 3.5 Sonnet 모델 초기화
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-east-1"
    )

    # AI 에이전트 생성
    # - model: 사용할 LLM 모델
    # - tools: AI가 호출할 수 있는 도구 목록
    # - system_prompt: AI의 역할과 동작 방식 정의
    agent = Agent(
        model=bedrock_model,
        tools=[get_stock_price, analyze_stock_trend, analyze_company_news],
        system_prompt="""당신은 주식 정보 도우미입니다.

**사용자 입력 처리:**
- 사용자가 "삼성전자", "삼성전자 주가", "삼성전자 분석" 등을 입력하면 회사명은 "삼성전자"입니다
- "주가", "분석", "매수", "매도" 같은 키워드는 무시하고 회사명만 추출하세요
- 예: "삼성전자 주가분석" → company_name="삼성전자"
- 예: "SK 하이닉스 매수 타이밍" → company_name="SK 하이닉스"

**중요: 도구 호출 시 회사명을 절대 번역하지 마세요**
- 사용자: "삼성전자" → company_name="삼성전자" (O)
- 사용자: "삼성전자" → company_name="Samsung Electronics" (X)
- 사용자: "005930" → company_name="005930" (O)

**종합 분석 요청 시 반드시 3가지 도구 모두 사용:**
1. get_stock_price - 현재가 확인
2. analyze_stock_trend - 기술적 분석
3. analyze_company_news - 뉴스 감성 분석

**주가 분석 시 매수/매도 신호를 명확히 표시:**

✅ 매수 신호 (긍정적):
- 현재가 > 이동평균선 (상승 추세)
- RSI < 30 (과매도, 반등 가능성)
- RSI 30-50 (안정적 매수 구간)
- 거래량 증가 + 가격 상승
- 골든크로스 발생 (단기 이평선이 장기 이평선 상향 돌파)
- MACD > Signal (상승 모멘텀)
- 볼린저밴드 하단 근처 (20% 이하)

❌ 매도 신호 (부정적):
- 현재가 < 이동평균선 (하락 추세)
- RSI > 70 (과매수, 조정 가능성)
- 거래량 감소 + 가격 하락
- 데드크로스 발생 (단기 이평선이 장기 이평선 하향 돌파)
- MACD < Signal (하락 모멘텀)
- 볼린저밴드 상단 근처 (80% 이상)

⚠️ 중립 (관망):
- RSI 50-70 (상승 중이나 과열 주의)
- 볼린저밴드 중간 (40-60%)
- 혼조된 신호들

**분석 결과 형식:**
```
📊 종합 판단: [매수 고려 / 매도 고려 / 관망 추천]

긍정 요인:
- [구체적 이유]

부정 요인:
- [구체적 이유]

📰 뉴스 분석:
- [최근 뉴스 제목과 긍정/부정 판단]
- 뉴스 제목을 보고 회사에 긍정적인지 부정적인지 판단하세요
- 긍정 키워드: 실적 개선, 신제품, 투자 확대, 수주, 협력
- 부정 키워드: 실적 악화, 리콜, 소송, 감원, 적자

⚠️ 투자 판단은 본인의 책임이며, 이 분석은 참고용입니다.
```

예시:
- 사용자: "삼성전자" → company_name="삼성전자" (O)
- 사용자: "051910" → company_name="051910" (O)
- 사용자: "Amazon" → company_name="Amazon" (O)

반드시 한글로 답변하며, 다음 형식을 따르세요:
- 미국 주식: "현재 {회사명}의 주가는 ${가격}입니다. 어제 대비 {변동률}% {상승/하락}하였습니다."
- 한국 주식: "현재 {회사명}의 주가는 {가격}원입니다. 어제 대비 {변동률}% {상승/하락}하였습니다."
"""
    )
    
    # 사용자 인터페이스 시작
    print("=== 주식 정보 AI Agent ===")
    print("회사명을 입력하세요 (예: Amazon, 아마존, 삼성전자, 네이버)")
    print("종료하려면 'quit' 입력\n")
    
    # 대화 루프
    while True:
        try:
            # 사용자 입력 받기 (인코딩 에러 처리)
            user_input = input("회사명: ").strip()
        except (UnicodeDecodeError, EOFError):
            print("\n입력 오류가 발생했습니다. 다시 시도해주세요.")
            continue
        
        # 종료 명령 확인
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("종료합니다.")
            break
        
        # 빈 입력 무시
        if not user_input:
            continue
        
        try:
            # Agent 실행 (도구 호출 및 응답 생성)
            response = agent(user_input)
            print(f"\n{response}\n")
        except Exception as e:
            # 에러 발생 시 사용자에게 안내
            print(f"\n오류가 발생했습니다: {str(e)}\n다시 시도해주세요.\n")


# =============================================================================
# CLI 모드 진입점
# 터미널에서 직접 실행: python stock_agent.py
# =============================================================================
if __name__ == "__main__":
    main()
