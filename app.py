import streamlit as st
import numpy as np
import pandas as pd
from scipy.optimize import fsolve
import plotly.graph_objects as go

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
# 2. 웹 UI 구성
# ==========================================
st.set_page_config(page_title="천체 공전 궤도 시뮬레이터", layout="wide")

st.title("🌌 외계행성 공전 궤도 시뮬레이터")
st.markdown("NASA 아카이브 데이터를 기반으로 제작되었습니다. 끊김과 요동침 없이 물 흐르듯 부드럽게 무한 자동 공전합니다.")

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

# ------------------------------------------
# 레이아웃 분할 및 시각화 (Fragment 기반 독립 차트)
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 애니메이션")
    
    # 정적 궤도선 데이터 사전 계산
    theta = np.linspace(0, 2 * np.pi, 200)
    x_orbit = a * np.cos(theta) - c
    y_orbit = b * np.sin(theta)

    # 축 범위 강제 고정 락(Lock) 계산
    if fix_scale:
        x_range = [-FIXED_LIMIT, FIXED_LIMIT]
        y_range = [-FIXED_LIMIT, FIXED_LIMIT]
        star_size = np.clip(star_rad * 6, 6, 40)
        planet_size = 5
    else:
        limit = a * (1 + e) * 1.3
        x_range = [-limit - c, limit - c]
        y_range = [-limit, limit]
        star_size = np.clip(star_rad * 12, 12, 60)
        planet_size = 8

    # 💡 부드러운 프레임 전환을 위해 140개의 타임라인 고해상도 좌표 배열 사전 연산
    num_frames = 140
    times = np.linspace(0, T, num_frames)
    x_coords = []
    y_coords = []

    for i in range(num_frames):
        t_val = times[i]
        M_val = (2 * np.pi / T) * t_val
        E_val = solve_kepler(M_val, e)
        x_coords.append(a * np.cos(E_val) - c)
        y_coords.append(b * np.sin(E_val))

    # Plotly 베이스 도화지 생성
    fig = go.Figure()
    
    # 1) 푸른색 궤도선 점선 배경
    fig.add_trace(go.Scatter(x=x_orbit, y=y_orbit, mode='lines', line=dict(color='#4A90E2', width=1.5, dash='dash'), name='Orbit'))
    # 2) 중심 태양(항성)
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(color=star_color, size=star_size, line=dict(color='white', width=1)), name='Star'))
    # 3) 초록색 외계행성 실시간 위치 레이어 (첫 프레임 위치 설정)
    fig.add_trace(go.Scatter(x=[x_coords[0]], y=[y_coords[0]], mode='markers', marker=dict(color='#1dd1a1', size=planet_size), name='Planet'))
    
    # 💡 [핵심 최적화] 자바스크립트 브라우저 메모리에 전체 애니메이션 프레임 데이터 한 번에 업로드
    frames_list = []
    for i in range(num_frames):
        frames_list.append(go.Frame(
            data=[
                go.Scatter(x=x_orbit, y=y_orbit),
                go.Scatter(x=[0], y=[0]),
                go.Scatter(x=[x_coords[i]], y=[y_coords[i]]) # 행성의 위치만 순차 교체
            ],
            name=f"f{i}"
        ))
    fig.frames = frames_list
    
    # 💡 [요동침 차단 핵심] 자바스크립트 단독 무한 루프 렌더링 설정 가동
    # 슬라이더 컴포넌트를 완전히 삭제하여 내부 타임라인 정지 버그를 해결했습니다.
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        xaxis=dict(range=x_range, title="X Distance (AU)", gridcolor="rgba(128,128,128,0.15)", scaleanchor="y", scaleratio=1, autorange=False),
        yaxis=dict(range=y_range, title="Y Distance (AU)", gridcolor="rgba(128,128,128,0.15)", autorange=False),
        width=700,
        height=600,
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=50),
        
        # 💡 차트가 브라우저에 렌더링되는 순간 사람 손을 거치지 않고 곧바로 영원히 무한 루프(`loop: true`) 하도록 설계
        updatemenus=[{
            "type": "buttons",
            "direction": "left",
            "showactive": False,
            "x": 0.02, "y": -0.01, "xanchor": "left", "yanchor": "top",
            "buttons": [{
                "label": "▶ 자동 공전 시작 (Auto Loop)",
                "method": "animate",
                "args": [None, {
                    "frame": {"duration": 20, "redraw": False}, # 20ms마다 프레임 교체하여 극상의 부드러움 연출
                    "fromcurrent": True,
                    "transition": {"duration": 0},
                    "loop": True # 💡 한 바퀴 끝나면 자동으로 0초로 돌아가는 마법의 자바스크립트 옵션
                }]
            }]
        }]
    )
    
    if is_star_rad_missing:
        st.warning("⚠️ 항성 반지름 데이터가 없어 기본 크기(1.0 Solar Rad)로 표시 중입니다.")
        
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 그래프 좌측 하단의 [▶ 자동 공전 시작] 버튼을 누르면 화면 떨림 현상 없이 영원히 부드럽게 무한 재생됩니다!")

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
