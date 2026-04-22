import streamlit as st
import requests
from datetime import datetime
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
import os

load_dotenv()

# ── Claude LLM 설정
claude_llm = LLM(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

# ── 페이지 설정
st.set_page_config(page_title="Simon's Crypto Dashboard", page_icon="📊", layout="wide")
st.title("📊 Simon's Crypto Portfolio Dashboard")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 데이터: CoinGecko")

# ── 보유 코인 설정
PORTFOLIO = {
    "BTC":  {"name": "Bitcoin",     "sector": "메이저"},
    "ETH":  {"name": "Ethereum",    "sector": "메이저"},
    "SOL":  {"name": "Solana",      "sector": "메이저"},
    "AAVE": {"name": "Aave",        "sector": "DeFi"},
    "SEI":  {"name": "Sei",         "sector": "DeFi"},
    "DOGE": {"name": "Dogecoin",    "sector": "밈코인"},
    "PEPE": {"name": "Pepe",        "sector": "밈코인"},
    "RIF":  {"name": "Rifampicin",  "sector": "DeSci"},
    "URO":  {"name": "Urolithin A", "sector": "DeSci"},
}

# ── CoinGecko ID 매핑
COINGECKO_IDS = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "SOL":  "solana",
    "AAVE": "aave",
    "SEI":  "sei-network",
    "DOGE": "dogecoin",
    "PEPE": "pepe",
    "RIF":  "rifampicin",
    "URO":  "urolithin-a",
}

# ── 가격 데이터 (CoinGecko, 5분 캐시)
@st.cache_data(ttl=300)
def get_prices():
    ids = ",".join(COINGECKO_IDS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except:
        return {}

# ── 가격 표시
prices = get_prices()

sectors = {}
for symbol, info in PORTFOLIO.items():
    s = info["sector"]
    if s not in sectors:
        sectors[s] = []
    sectors[s].append(symbol)

for sector, symbols in sectors.items():
    icon = {"메이저": "🔵", "DeFi": "🟡", "밈코인": "🟢", "DeSci": "🔴"}.get(sector, "⚪")
    st.subheader(f"{icon} {sector}")
    cols = st.columns(len(symbols))
    for i, symbol in enumerate(symbols):
        cg_id = COINGECKO_IDS.get(symbol)
        data = prices.get(cg_id, {})
        price = data.get("usd") or 0
        change = data.get("usd_24h_change") or 0
        arrow = "▲" if change >= 0 else "▼"
        with cols[i]:
            if price == 0:
                st.metric(label=symbol, value="데이터 없음", delta="-")
            elif price < 0.0001:
                st.metric(label=symbol, value=f"${price:.8f}", delta=f"{arrow} {abs(change):.2f}%")
            elif price < 1:
                st.metric(label=symbol, value=f"${price:.4f}", delta=f"{arrow} {abs(change):.2f}%")
            else:
                st.metric(label=symbol, value=f"${price:,.2f}", delta=f"{arrow} {abs(change):.2f}%")

st.divider()

# ── AI 분석 섹션
st.subheader("🤖 AI 포트폴리오 분석")
st.caption("Claude AI가 현재 포트폴리오를 분석해드립니다 (API 비용 발생)")

if st.button("🔍 AI 분석 시작", type="primary"):
    with st.spinner("AI Agent들이 분석 중입니다..."):

        price_summary = []
        for symbol, info in PORTFOLIO.items():
            cg_id = COINGECKO_IDS.get(symbol)
            data = prices.get(cg_id, {})
            price = data.get("usd") or 0
            change = data.get("usd_24h_change") or 0
            price_summary.append(f"{symbol}({info['sector']}): ${price:.6f} | 24h: {change:.2f}%")
        price_text = "\n".join(price_summary)

        analyst = Agent(
            role="크립토 포트폴리오 분석가",
            goal="보유 코인의 현재 상태를 분석하고 섹터별 리스크와 기회를 파악한다",
            backstory="10년 경력의 크립토 애널리스트로 DeFi, 밈코인, DeSci, 메이저 코인 전반에 걸쳐 깊은 통찰력을 가지고 있다.",
            verbose=False,
            llm=claude_llm,
        )

        advisor = Agent(
            role="투자 전략 어드바이저",
            goal="분석 결과를 바탕으로 실용적인 투자 인사이트를 제공한다",
            backstory="리스크 관리와 사이클 투자 전략 전문가로, 감정 배제한 데이터 기반 조언을 제공한다.",
            verbose=False,
            llm=claude_llm,
        )

        analysis_task = Task(
            description=f"""
            아래는 현재 보유 포트폴리오 현황이다 (CoinGecko 실시간 데이터):
            {price_text}

            다음을 분석해라:
            1. 섹터별 (메이저/DeFi/밈코인/DeSci) 24시간 성과 요약
            2. 가장 주목할 코인 (상승/하락 기준)
            3. 현재 시장 분위기 판단
            """,
            agent=analyst,
            expected_output="섹터별 분석과 주목 코인을 포함한 현황 리포트"
        )

        advice_task = Task(
            description="""
            분석 결과를 바탕으로 Simon에게 실용적인 인사이트를 제공해라.
            Simon의 전략: 메이저 3개(BTC/ETH/SOL) 장기보유, 알트는 사이클 트레이딩, DeSci(RIF/URO)는 고위험 소액 포지션

            다음을 포함해라:
            1. 현재 포트폴리오에서 주의할 점 1가지
            2. 긍정적인 신호 1가지
            3. 한 줄 요약

            간결하고 직접적으로 작성해라.
            """,
            agent=advisor,
            expected_output="실용적인 투자 인사이트 3가지와 한 줄 요약"
        )

        crew = Crew(
            agents=[analyst, advisor],
            tasks=[analysis_task, advice_task],
            verbose=False,
        )

        result = crew.kickoff()

        st.success("분석 완료!")
        st.markdown(str(result))

st.divider()
st.caption("💡 가격 데이터: CoinGecko API (5분 캐시) | AI 분석: Claude API")