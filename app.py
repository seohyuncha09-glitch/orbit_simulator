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
    
    # 💡 [진짜 해결책] 연산 및 대시보드 출력에 필요한 모든 물리 컬럼을 검사합니다.
    # 하나라도 빈 값(NaN)이 있으면 검색 목록에서 아예 제외합니다.
    required_cols = ['pl_orbsmax', 'pl_orbper', 'pl_orbeccen', 'st_rad', 'st_teff', 'st_mass']
    
    for col in required_cols:
        if col in df_raw.columns:
            df_raw = df_raw[df_raw[col].notna()]
            
    # 물리적으로 유효한 양수 데이터만 필터링
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
    st.error("⚠️ 모든 필수 물리량(장반경, 주기, 이심률, 항성 반지름/온도/질량)이 완벽히 채워진 행성 데이터가 없습니다.")
    st.stop()

FIXED_LIMIT = 15.0

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
st.markdown("정밀 가공된 NASA 아카이브 데이터를 기반으로 구동되는 부하 제로 시뮬레이터입니다.")

# 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
fix_scale = st.sidebar.checkbox("시뮬레이션 축 범위 고정 (⚠️천체 크기 연동)", value=False)
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]

a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen'])
T = float(p_data['pl_orbper'])

# 타원 궤도 기하학 연산
b = a * np.sqrt(1 - e**2)
c = a * e
mu = (4 * np.pi**2 * (a**3)) / (T**2)

# 항성 정보 매핑
star_rad = float(p_data['st_rad'])
star_teff = float(p_data['st_teff'])
star_mass = float(p_data['st_mass'])
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
    v_au_day = np.sqrt(mu * (2 / r_val - 1 / a)) if r_val > 0 else 0.0
    v_kms = v_au_day * 149597870.7 / 86400
    speeds.append(v_kms)

# 정적 궤도선 데이터
theta = np.linspace(0, 2 * np.pi, 200)
x_orbit = a * np.cos(theta) - c
y_orbit = b * np.sin(theta)

# 크기 및 축 범위 매핑
if fix_scale:
    x_range = [-FIXED_LIMIT, FIXED_LIMIT]
    y_range = [-FIXED_LIMIT, FIXED_LIMIT]
    star_size = np.clip(star_rad * 3, 5, 40)
    planet_size = 5
else:
    limit = a * 1.3
    x_range = [float(-limit - c), float(limit - c)]
    y_range = [float(-limit), float(limit)]
    star_size = np.clip(star_rad * 12, 10, 60)
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
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(color=star_color, size=star_size, line=dict(color='white', width=0.5)), name='Star'))
    fig.add_trace(go.Scatter(x=[x_coords[0]], y=[y_coords[0]], mode='markers', marker=dict(color='#1dd1a1', size=planet_size), name='Planet'))
    
    # 프레임 데이터 리스트 구축
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
    
    # 버튼 컨트롤러 설정
    play_button = {
        "label": "▶ Play", 
        "method": "animate", 
        "args": [None, {"frame": {"duration": 25, "redraw": False}, "fromcurrent": True, "transition": {"duration": 0}, "loop": True}]
    }
    pause_button = {
        "label": "⏸ Pause", 
        "method": "animate", 
        "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]
    }
    
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
        xaxis=dict(range=x_range, title="X Distance (AU)", gridcolor="rgba(128,128,128,0.15)", scaleanchor="y", scaleratio=1, showzeroline=False),
        yaxis=dict(range=y_range, title="Y Distance (AU)", gridcolor="rgba(128,128,128,0.15)", showzeroline=False),
        width=700,
        height=650,
        showlegend=False,
        updatemenus=[menu_dict],
        sliders=[slider_dict]
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 데이터 대시보드")
    
    # 💡 모든 변수가 float임이 상단에서 100% 검증되었으므로 포맷팅 에러가 절대 나지 않습니다.
    info_text = (
        f"### 🪐 행성 특성 정보\n"
        f"* **이름:** `{p_data['pl_name']}`\n"
        f"* **공전 주기:** `{T:.1f} 일` \n"
        f"* **궤도 장반경 (거리):** `{a:.3f} AU` \n"
        f"* **궤도 이심률 (타원형 정도):** `{e:.3f}` \n"
        f"* **행성 반지름:** `정보 없음 (화면 고정)` \n\n"
        f"### ☀️ 중심 항성(별) 정보\n"
        f"* **분광형 유형:** `{spectral_type}` \n"
        f"* **표면 온도:** `{star_teff:.1f} K` \n"
        f"* **항성 반지름:** `{star_rad:.3f} Solar Rad` \n"
        f"* **항성 질량:** `{star_mass:.3f} Solar Mass`"
    )
    st.markdown(info_text)
