import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import fsolve
import time

# 한글 폰트 설정 (웹 서버 환경용 안전장치)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

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
    if teff >= 10000: return '#9bb0ff', 'O / B (푸른색)'
    elif teff >= 7500: return '#aabfff', 'A (청백색)'
    elif teff >= 6000: return '#f8f7ff', 'F (백색)'
    elif teff >= 5200: return '#fff4ea', 'G (황백색)'
    elif teff >= 3700: return '#ffd2a1', 'K (주황색)'
    else: return '#ff8585', 'M (적색)'

def solve_kepler(M, e):
    func = lambda E: E - e * np.sin(E) - M
    return fsolve(func, M)[0]

# ==========================================
# 2. 웹 UI 구성 및 자동 애니메이션 변수 제어
# ==========================================
st.set_page_config(page_title="천체 공전 궤도 시뮬레이터", layout="wide")

st.title("🌌 외계행성 공전 궤도 시뮬레이터")
st.markdown("NASA 외계행성 아카이브 데이터를 기반으로 작동하는 정밀 궤도 시뮬레이터입니다.")

# 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
fix_scale = st.sidebar.checkbox("시뮬레이션 축 범위 고정 (⚠️천체 크기 연동)", value=False)
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names)

# 애니메이션 재생/일시정지 버튼 추가
is_playing = st.sidebar.checkbox("▶️ 자동 공전 애니메이션 재생", value=True)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]
a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen']) if not pd.isna(p_data['pl_orbeccen']) else 0.0
T = float(p_data['pl_orbper'])

b = a * np.sqrt(1 - e**2)
c = a * e
mu = (4 * np.pi**2 * (a**3)) / (T**2) if T > 0 else 1.0

# 💡 [핵심] 웹 세션 상태(Session State)를 이용해 자동으로 흘러갈 시간을 저장합니다.
if "sim_time" not in st.session_state or st.sidebar.button("🔄 시간 초기화"):
    st.session_state.sim_time = 0.0

# 행성 공전주기에 맞춰 프레임당 흐를 시간(dt)을 계산
if T < 10:
    dt = T / 80.0
elif T < 100:
    dt = T / 150.0
else:
    dt = np.clip(T / 250.0, 0.5, 5.0)

# ------------------------------------------
# 레이아웃 분할 및 시각화
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 애니메이션")
    
    # 슬라이더가 현재 누적된 자동 시간(sim_time)을 반영하도록 설정
    # 사용자가 슬라이더를 강제로 조작하면 그 시간대로 고정 및 동기화됩니다.
    time_slider = st.slider(
        "궤도 시간 진행도 (일)", 
        min_value=0.0, 
        max_value=float(T), 
        value=float(np.clip(st.session_state.sim_time, 0.0, T)),
        step=float(np.clip(T/100, 0.1, 5.0))
    )
    
    # 사용자가 마우스로 슬라이더를 건드렸다면 그 값을 세션 시간에 수동 반영
    if abs(time_slider - st.session_state.sim_time) > (dt * 1.5):
        st.session_state.sim_time = time_slider

    # 그래프 그리기
    fig, ax_sim = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor('#111111')
    ax_sim.set_facecolor('#111111')
    ax_sim.set_aspect('equal', adjustable='box')
    ax_sim.grid(True, linestyle='--', alpha=0.2, color='gray')
    ax_sim.tick_params(colors='white')
    ax_sim.set_xlabel("X 거리 (AU)", color='white')
    ax_sim.set_ylabel("Y 거리 (AU)", color='white')
    
    # 궤도선
    theta = np.linspace(0, 2 * np.pi, 300)
    ax_sim.plot(a * np.cos(theta) - c, b * np.sin(theta), color='#4A90E2', linestyle='--', linewidth=1.2)
    
    # 항성 크기 및 축 범위 매핑
    is_star_rad_missing = 'st_rad' not in p_data or pd.isna(p_data['st_rad'])
    star_rad = 1.0 if is_star_rad_missing else float(p_data['st_rad'])
    star_teff = p_data['st_teff'] if 'st_teff' in p_data else np.nan
    star_color, spectral_type = get_star_color_and_type(star_teff)
    
    if fix_scale:
        ax_sim.set_xlim(-FIXED_LIMIT, FIXED_LIMIT)
        ax_sim.set_ylim(-FIXED_LIMIT, FIXED_LIMIT)
        star_marker_size = np.clip(star_rad * 15, 10, 150)
        planet_marker_size = 4.5
    else:
        limit = a * 1.3
        ax_sim.set_xlim(-limit - c, limit - c)
        ax_sim.set_ylim(-limit, limit)
        star_marker_size = np.clip(star_rad * 140, 35, 500)
        planet_marker_size = 7.5
        
    # 항성 그리기
    ax_sim.scatter(0, 0, color=star_color, s=star_marker_size, edgecolor='white', linewidth=0.5, zorder=5)
    
    # 현재 시간의 행성 위치 계산
    M = (2 * np.pi / T) * st.session_state.sim_time
    E = solve_kepler(M, e)
    x = a * np.cos(E) - c
    y = b * np.sin(E)
    
    r = np.sqrt((x + c)**2 + y**2)
    v_au_day = np.sqrt(mu * (2/r - 1/a))
    v_kms = v_au_day * 149597870.7 / 86400
    
    # 행성 그리기
    ax_sim.plot(x, y, 'o', markersize=planet_marker_size, color='#1dd1a1', zorder=6)
    
    # 텍스트 오버레이
    ax_sim.text(0.05, 0.94, f"Time: {st.session_state.sim_time:.1f} / {T:.1f} days", transform=ax_sim.transAxes, color='white', fontsize=10, fontweight='bold')
    ax_sim.text(0.05, 0.89, f"Speed: {v_kms:.2f} km/s", transform=ax_sim.transAxes, color='#1dd1a1', fontsize=10, fontweight='bold')
    
    if is_star_rad_missing:
        st.warning("⚠️ 항성 반지름 데이터가 없어 기본 크기(1.0 Solar Rad)로 표시 중입니다.")
        
    st.pyplot(fig)

with col2:
    st.subheader("📊 데이터 대시보드")
    def check_val(val, unit=""): return f"{val:.3f} {unit}" if not pd.isna(val) else "정보 없음"
    star_rad_display = "정보 없음 (기본값)" if is_star_rad_missing else f"{star_rad:.3f} Solar Rad"
    
    st.markdown(f"""
    ### 🪐 행성 특성 정보
    * **이름:** `{p_data['pl_name']}`
    * **공전 주기:** `{T:.1f} 일`
    * **궤도 장반경 (거리):** `{a:.3f} AU`
    * **궤도 이심률 (타원형 정도):** `{e:.3f}`
    * **행성 반지름:** `정보 없음 (화면 고정)`
    
    ### ☀️ 중심 항성(별) 정보
    * **분광형 유형:** `{spectral_type}`
    * **표면 온도:** `{check_val(star_teff, 'K')}`
    * **항성 반지름:** `{star_rad_display}`
    * **항성 질량:** `{check_val(p_data['st_mass'] if 'st_mass' in p_data else np.nan, 'Solar Mass')}`
    """)

# 💡 [핵심] 자동 재생 체크박스가 활성화되어 있으면, 시간을 dt만큼 늘리고 브라우저를 즉시 새로고침합니다.
if is_playing:
    time.sleep(0.03)  # 부드러운 프레임을 위한 아주 미세한 딜레이 (약 30fps 목표)
    st.session_state.sim_time += dt
    if st.session_state.sim_time > T:
        st.session_state.sim_time = 0.0
    st.rerun()  # 💡 코드를 처음부터 다시 실행시켜 화면을 실시간 업데이트!al(p_data['st_mass'] if 'st_mass' in p_data else np.nan, 'Solar Mass')}`
    """)
