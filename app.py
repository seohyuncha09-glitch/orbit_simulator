import streamlit as st
import numpy as np
import pandas as pd
from scipy.optimize import fsolve
import plotly.graph_objects as go

# ==========================================
# 1. 데이터 불러오기 및 불완전 데이터 원천 배제
# ==========================================
@st.cache_data
def load_data():
    df_raw = pd.read_csv("PS_data.csv")
    
    # 필수 물리 컬럼 검사 및 결측치 제거
    required_cols = ['pl_orbsmax', 'pl_orbper', 'pl_orbeccen', 'st_rad', 'st_teff', 'st_mass']
    for col in required_cols:
        if col in df_raw.columns:
            df_raw = df_raw[df_raw[col].notna()]
            
    # 유효한 양수 데이터만 필터링
    df_raw = df_raw[df_raw['pl_orbsmax'] > 0]
    df_raw = df_raw[df_raw['pl_orbper'] > 0]
    df_raw = df_raw[df_raw['st_rad'] > 0]
    df_raw = df_raw[df_raw['st_teff'] > 0]
    df_raw = df_raw[df_raw['st_mass'] > 0]
    
    return df_raw

try:
    df = load_data()
    all_planet_names = sorted(df['pl_name'].dropna().unique())
except Exception as e:
    st.error("CSV 파일을 찾을 수 없거나 데이터 필터링 중 오류가 발생했습니다.")
    st.stop()

if not all_planet_names:
    st.error("⚠️ 조건에 맞는 완전한 행성 데이터가 없습니다.")
    st.stop()

def get_star_color_and_type(teff):
    if teff >= 10000: return '#9bb0ff', 'O / B'
    elif teff >= 7500: return '#aabfff', 'A'
    elif teff >= 6000: return '#f8f7ff', 'F'
    elif teff >= 5200: return '#fff4ea', 'G'
    elif teff >= 3700: return '#ffd2a1', 'K'
    else: return '#ff8585', 'M'

def solve_kepler(M, e):
    func = lambda E: E - e * np.sin(E) - M
    return fsolve(func, M)[0]

# ==========================================
# 2. 웹 UI 구성
# ==========================================
st.set_page_config(page_title="천체 공전 궤도 시뮬레이터", layout="wide")

st.title("🌌 외계행성 공전 궤도 시뮬레이터")
st.markdown("정밀 가공된 NASA 아카이브 데이터를 기반으로 구동되는 시뮬레이터입니다.")

# 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]

a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen'])
T = float(p_data['pl_orbper'])

b = a * np.sqrt(1 - e**2)
c = a * e
mu = (4 * np.pi**2 * (a**3)) / (T**2)

star_rad = float(p_data['st_rad'])
star_teff = float(p_data['st_teff'])
star_mass = float(p_data['st_mass'])
star_color, spectral_type = get_star_color_and_type(star_teff)

# 💡 [버그 원천 차단] 복잡한 Plotly 내장 애니메이션 대신 Streamlit 슬라이더로 상호작용 구현
st.sidebar.markdown("---")
st.sidebar.subheader("🏃 궤도 시점 제어")
current_day = st.sidebar.slider("진행 시간 (일)", min_value=0.0, max_value=T, value=0.0, step=max(0.1, T/100))

# 현재 시점의 행성 위치 및 속도 계산
M_curr = (2 * np.pi / T) * current_day
E_curr = solve_kepler(M_curr, e)
x_curr = float(a * np.cos(E_curr) - c)
y_curr = float(b * np.sin(E_curr))

r_curr = np.sqrt((x_curr + c)**2 + y_curr**2)
v_au_day = np.sqrt(mu * (2 / r_curr - 1 / a)) if r_curr > 0 else 0.0
v_kms = v_au_day * 149597870.7 / 86400

# 정적 궤도선 데이터 고정 생성
theta = np.linspace(0, 2 * np.pi, 200)
x_orbit = a * np.cos(theta) - c
y_orbit = b * np.sin(theta)

star_size = np.clip(star_rad * 12, 10, 50)

# ------------------------------------------
# 레이아웃 분할 및 시각화
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 실시간 플롯")
    
    # 메인 그래픽스 객체 바인딩
    fig = go.Figure()
    
    # 1. 궤도선
    fig.add_trace(go.Scatter(x=x_orbit, y=y_orbit, mode='lines', line=dict(color='#4A90E2', width=1.5, dash='dash'), name='Orbit'))
    # 2. 중심 항성
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(color=star_color, size=star_size, line=dict(color='white', width=0.5)), name='Star'))
    # 3. 현재 시점의 행성 위치
    fig.add_trace(go.Scatter(x=[x_curr], y=[y_curr], mode='markers', marker=dict(color='#1dd1a1', size=10), name='Planet'))
    
    # 💡 에러를 내뿜던 복잡한 슬라이더/메뉴 속성을 전부 배제하고, 순수한 레이아웃 옵션만 안전하게 주입
    fig.layout.title = f"<b>🪐 {selected_planet} (Day: {current_day:.1f} / {T:.1f}) | Speed: {v_kms:.2f} km/s</b>"
    fig.layout.template = "plotly_dark"
    fig.layout.paper_bgcolor = "#111111"
    fig.layout.plot_bgcolor = "#111111"
    fig.layout.xaxis = dict(title="X Distance (AU)", gridcolor="rgba(128,128,128,0.15)", showzeroline=False)
    fig.layout.yaxis = dict(title="Y Distance (AU)", gridcolor="rgba(128,128,128,0.15)", showzeroline=False)
    fig.layout.width = 650
    fig.layout.height = 650
    fig.layout.showlegend = False
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 데이터 대시보드")
    
    info_text = (
        f"### 🪐 행성 특성 정보\n"
        f"* **이름:** `{p_data['pl_name']}`\n"
        f"* **공전 주기:** `{T:.1f} 일` \n"
        f"* **궤도 장반경 (거리):** `{a:.3f} AU` \n"
        f"* **궤도 이심률 (타원형 정도):** `{e:.3f}` \n"
        f"* **현재 실시간 공전 속도:** `{v_kms:.2f} km/s` \n\n"
        f"### ☀️ 중심 항성(별) 정보\n"
        f"* **분광형 유형:** `{spectral_type}` \n"
        f"* **표면 온도:** `{star_teff:.1f} K` \n"
        f"* **항성 반지름:** `{star_rad:.3f} Solar Rad` \n"
        f"* **항성 질량:** `{star_mass:.3f} Solar Mass`"
    )
    st.markdown(info_text)
