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
st.markdown("NASA 아카이브 데이터를 기반으로 브라우저 자체 애니메이션 렌더링을 적용해 부하를 최소화한 버전입니다.")

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
# 모든 프레임 위치 및 속도 계산
# ------------------------------------------
num_frames = 120
times = np.linspace(0, T, num_frames)

x_coords = []
y_coords = []
speeds = []

for t in times:
    M = (2 * np.pi / T) * t
    E = solve_kepler(M, e)
    x_val = a * np.cos(E) - c
    y_val = b * np.sin(E)
    x_coords.append(x_val)
    y_coords.append(y_val)
    
    r_val = np.sqrt((x_val + c)**2 + y_val**2)
    if r_val > 0 and (2 / r_val - 1 / a) > 0:
        v_au_day = np.sqrt(mu * (2 / r_val - 1 / a))
    else:
        v_au_day = 0.0
    speeds.append(v_au_day * 149597870.7 / 86400)

# 정적 궤도선 데이터
theta = np.linspace(0, 2 * np.pi, 200)
x_orbit = a * np.cos(theta) - c
y_orbit = b * np.sin(theta)

# ------------------------------------------
# 🛠️ [수정 부분] 항성이 너무 크게 나오는 현상 해결
# ------------------------------------------
if fix_scale:
    x_range = [-FIXED_LIMIT, FIXED_LIMIT]
    y_range = [-FIXED_LIMIT, FIXED_LIMIT]
    # 축 범위가 넓을 때 항성 크기 축소 (최대 40픽셀 제한)
    star_size = np.clip(star_rad * 6, 6, 40)
    planet_size = 5
else:
    limit = a * 1.3
    x_range = [-limit - c, limit - c]
    y_range = [-limit, limit]
    # 💡 자동 확대 줌 모드에서 기존 35배 -> 12배로 낮추고 최댓값을 60픽셀로 대폭 줄임
    star_size = np.clip(star_rad * 12, 12, 60)
    planet_size = 8

# ------------------------------------------
# 레이아웃 분할 및 시각화
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 애니메이션")
    
    fig = go.Figure()
    
    # 기본 레이어 추가
    fig.add_trace(go.Scatter(x=x_orbit, y=y_orbit, mode='lines', line=dict(color='#4A90E2', width=1.5, dash='dash'), name='Orbit'))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(color=star_color, size=star_size, line=dict(color='white', width=1)), name='Star'))
    fig.add_trace(go.Scatter(x=[x_coords[0]], y=[y_coords[0]], mode='markers', marker=dict(color='#1dd1a1', size=planet_size), name='Planet'))
    
    # 괄호 구조 최적화 루프
    frames_list = []
    for i in range(num_frames):
        frame_data = [
            go.Scatter(x=x_orbit, y=y_orbit),
            go.Scatter(x=[0], y=[0]),
            go.Scatter(x=[x_coords[i]], y=[y_coords[i]])
        ]
        frame_layout = go.Layout(
            title=dict(text=f"<b>Time: {times[i]:.1f} / {T:.1f} days<br><span style='color:#1dd1a1'>Speed: {speeds[i]:.2f} km/s</span></b>")
        )
        single_frame = go.Frame(data=frame_data, name=f"frame{i}", layout=frame_layout)
        frames_list.append(single_frame)
        
    fig.frames = frames_list
    
    # 컨트롤 UI 설정
    play_button = {"label": "▶ Play", "method": "animate", "args": [None, {"frame": {"duration": 25, "redraw": False}, "fromcurrent": True, "transition": {"duration": 0}}]}
    pause_button = {"label": "⏸ Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]}
    
    menu_dict = {
        "type": "buttons",
        "direction": "left",
        "pad": {"r": 10, "t": 10},
        "showactive": False,
        "x": 0.05, "xanchor": "left", "y": -0.1, "yanchor": "top",
        "buttons": [play_button, pause_button]
    }
    
    steps_list = []
    for i in range(num_frames):
        step = {
            "args": [[f"frame{i}"], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}],
            "label": f"{times[i]:.1f}",
            "method": "animate"
        }
        steps_list.append(step)
        
    slider_dict = {
        "active": 0,
        "yanchor": "top", "xanchor": "left",
        "currentvalue": {"font": {"size": 12, "color": "white"}, "prefix": "Day: ", "visible": True, "xanchor": "right"},
        "transition": {"duration": 0},
        "pad": {"b": 10, "t": 50}, "len": 0.9, "x": 0.05, "y": -0.15,
        "steps": steps_list
    }
    
    fig.update_layout(
        title=dict(text=f"<b>Time: 0.0 / {T:.1f} days<br><span style='color:#1dd1a1'>Speed: {speeds[0]:.2f} km/s</span></b>", x=0.05, y=0.95, font=dict(color='white', size=14)),
        template="plotly_dark",
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        xaxis=dict(range=x_range, title="X Distance (AU)", gridcolor="rgba(128,128,128,0.15)", scaleanchor="y", scaleratio=1),
        yaxis=dict(range=y_range, title="Y Distance (AU)", gridcolor="rgba(128,128,128,0.15)"),
        width=700,
        height=650,
        showlegend=False,
        updatemenus=[menu_dict],
        sliders=[slider_dict]
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
