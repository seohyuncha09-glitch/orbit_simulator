import streamlit as st
import numpy as np
import pandas as pd
from scipy.optimize import fsolve
import plotly.graph_objects as go
import time

# ==========================================
# 1. 데이터 불러오기
# ==========================================
@st.cache_data
def load_data():
    return pd.read_csv("PS_data.csv")

try:
    df = load_data()
    all_planet_names = sorted(df['pl_name'].dropna().unique())
except Exception as e:
    st.error("CSV 파일을 찾을 수 없습니다. GitHub 저장소에 'PS_data.csv' 파일이 있는지 확인해 주세요.")
    st.stop()

FIXED_LIMIT = 15.0

def get_star_color_and_type(teff):
    if pd.isna(teff): return '#FF9F43', 'Unknown'
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
# 2. 웹 UI 구성 및 세션 상태 정의
# ==========================================
st.set_page_config(page_title="천체 공전 궤도 시뮬레이터", layout="wide")

st.title("🌌 외계행성 공전 궤도 시뮬레이터")
st.markdown("NASA 아카이브 데이터를 기반으로 부하 없이 완벽한 무한 공전 루프가 적용된 버전입니다.")

# 💡 실시간 무한 루프 제어를 위한 핵심 세션 타이머 변수
if 'current_time' not in st.session_state:
    st.session_state.current_time = 0.0
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = True

# 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
fix_scale = st.sidebar.checkbox("시뮬레이션 축 범위 고정 (⚠️천체 크기 연동)", value=False)
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]
a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen']) if not pd.isna(p_data['pl_orbeccen']) else 0.0
T = float(p_data['pl_orbper'])

b = a * np.sqrt(1 - e**2)
c = a * e
mu = (4 * np.pi**2 * (a**3)) / (T**2) if T > 0 else 1.0

# 항성 정보 물리 매핑
is_star_rad_missing = 'st_rad' not in p_data or pd.isna(p_data['st_rad'])
star_rad = 1.0 if is_star_rad_missing else float(p_data['st_rad'])
star_teff = p_data['st_teff'] if 'st_teff' in p_data else np.nan
star_color, spectral_type = get_star_color_and_type(star_teff)

# 💡 애니메이션 재생 상태 토글 버튼
if st.sidebar.button("▶ 재생 / ⏸ 일시정지 토글"):
    st.session_state.is_playing = not st.session_state.is_playing

# ------------------------------------------
# 💡 [핵심 최적화] 무한 루프를 도는 현재 프레임의 위치 계산
# ------------------------------------------
# 공전 주기에 맞춰 한 프레임에 전진할 시간 단위(dt) 결정
dt = T / 100 if T > 0 else 1.0

# 만약 재생 상태라면 시간에 dt를 더해줌 (한 바퀴 돌면 0으로 완벽 리셋!)
if st.session_state.is_playing:
    st.session_state.current_time += dt
    if st.session_state.current_time >= T:
        st.session_state.current_time = 0.0

# 현재 타이밍의 행성 위치 및 속도 실시간 연산
M = (2 * np.pi / T) * st.session_state.current_time
E = solve_kepler(M, e)
x_val = a * np.cos(E) - c
y_val = b * np.sin(E)

r_val = np.sqrt((x_val + c)**2 + y_val**2)
if r_val > 0 and (2 / r_val - 1 / a) > 0:
    v_au_day = np.sqrt(mu * (2 / r_val - 1 / a))
else:
    v_au_day = 0.0
v_kms = v_au_day * 149597870.7 / 86400

# 정적 궤도선 데이터
theta = np.linspace(0, 2 * np.pi, 200)
x_orbit = a * np.cos(theta) - c
y_orbit = b * np.sin(theta)

# 크기 및 축 범위 매핑
if fix_scale:
    x_range = [-FIXED_LIMIT, FIXED_LIMIT]
    y_range = [-FIXED_LIMIT, FIXED_LIMIT]
    star_size = np.clip(star_rad * 6, 6, 40)
    planet_size = 5
else:
    limit = a * 1.3
    x_range = [-limit - c, limit - c]
    y_range = [-limit, limit]
    star_size = np.clip(star_rad * 12, 12, 60)
    planet_size = 8

# ------------------------------------------
# 레이아웃 분할 및 시각화
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 애니메이션")
    
    # 정적 차트만 출력하되, 시간의 변화를 Plotly가 가볍게 새로 갱신합니다.
    fig = go.Figure()
    
    # 1) 궤도선
    fig.add_trace(go.Scatter(x=x_orbit, y=y_orbit, mode='lines', line=dict(color='#4A90E2', width=1.5, dash='dash'), name='Orbit'))
    # 2) 중심 항성
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(color=star_color, size=star_size, line=dict(color='white', width=1)), name='Star'))
    # 3) 행성 실시간 좌표 위치 매핑
    fig.add_trace(go.Scatter(x=[x_val], y=[y_val], mode='markers', marker=dict(color='#1dd1a1', size=planet_size), name='Planet'))
    
    fig.update_layout(
        title=dict(text=f"<b>Time: {st.session_state.current_time:.1f} / {T:.1f} days<br><span style='color:#1dd1a1'>Speed: {v_kms:.2f} km/s</span></b>", x=0.05, y=0.95, font=dict(color='white', size=14)),
        template="plotly_dark",
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        xaxis=dict(range=x_range, title="X Distance (AU)", gridcolor="rgba(128,128,128,0.15)", scaleanchor="y", scaleratio=1),
        yaxis=dict(range=y_range, title="Y Distance (AU)", gridcolor="rgba(128,128,128,0.15)"),
        width=700,
        height=600,
        showlegend=False
    )
    
    if is_star_rad_missing:
        st.warning("⚠️ 항성 반지름 데이터가 없어 기본 크기(1.0 Solar Rad)로 표시 중입니다.")
        
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 데이터 대시보드")
    def check_val(val, unit=""): return f"{val:.3f} {unit}" if not pd.isna(val) else "정보 없음"
    star_rad_display = "정보 없음 (기본값)" if is_star_rad_missing else f"{star_rad:.3f} Solar Rad"
    
    info_text = (
        f"### 🪐 행성 특성 정보\n"
        f"* **이름:** `{p_data['pl_name']}`\n"
        f"* **공전 주기:** `{T:.1f} 일` \n"
        f"* **궤도 장반경 (거리):** `{a:.3f} AU` \n"
        f"* **궤도 이심률 (타원형 정도):** `{e:.3f}` \n"
        f"* **행성 반지름:** `정보 없음 (화면 고정)` \n\n"
        f"### ☀️ 중심 항성(별) 정보\n"
        f"* **분광형 유형:** `{spectral_type}` \n"
        f"* **표면 온도:** `{check_val(star_teff, 'K')}` \n"
        f"* **항성 반지름:** `{star_rad_display}` \n"
        f"* **항성 질량:** `{check_val(p_data['st_mass'] if 'st_mass' in p_data else np.nan, 'Solar Mass')}`"
    )
    st.markdown(info_text)

# 💡 [무한 루프 핵심] 부하 방지를 위해 0.04초(약 25 FPS) 쉬어준 뒤 화면을 강제로 계속 다시 그립니다.
if st.session_state.is_playing:
    time.sleep(0.04)
    st.rerun()
