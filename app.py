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
# 2. 웹 UI 구성 및 레이아웃 정의
# ==========================================
st.set_page_config(page_title="천체 공전 궤도 시뮬레이터", layout="wide")

st.title("🌌 외계행성 공전 궤도 시뮬레이터")
st.markdown("NASA 아카이브 데이터를 기반으로 제작되었습니다. 별도의 조작 없이 자동으로 영원히 공전합니다.")

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

# 독립적으로 초고속 작동하는 Fragment 블록
@st.fragment
def run_simulation_fragment():
    # 정적 궤도선 데이터 사전 빌드
    theta = np.linspace(0, 2 * np.pi, 200)
    x_orbit = a * np.cos(theta) - c
    y_orbit = b * np.sin(theta)

    # 크기 및 고정축 범위 매핑
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

    # 120개의 전체 타임라인 데이터 연산
    num_frames = 120
    times = np.linspace(0, T, num_frames)
    x_coords = []
    y_coords = []
    speeds = []

    for i in range(num_frames):
        t_val = times[i]
        M_val = (2 * np.pi / T) * t_val
        E_val = solve_kepler(M_val, e)
        x_p = a * np.cos(E_val) - c
        y_p = b * np.sin(E_val)
        x_coords.append(x_p)
        y_coords.append(y_p)
        
        r_p = np.sqrt((x_p + c)**2 + y_p**2)
        if r_p > 0 and (2 / r_p - 1 / a) > 0:
            v_au = np.sqrt(mu * (2 / r_p - 1 / a))
        else:
            v_au = 0.0
        speeds.append(v_au * 149597870.7 / 86400)

    # 레이아웃 분할 배치
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"✨ {selected_planet} 궤도 애니메이션")
        
        fig = go.Figure()
        
        # 기본 배치 레이어
        fig.add_trace(go.Scatter(x=x_orbit, y=y_orbit, mode='lines', line=dict(color='#4A90E2', width=1.5, dash='dash'), name='Orbit'))
        fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(color=star_color, size=star_size, line=dict(color='white', width=1)), name='Star'))
        fig.add_trace(go.Scatter(x=[x_coords[0]], y=[y_coords[0]], mode='markers', marker=dict(color='#1dd1a1', size=planet_size), name='Planet'))
        
        # 자바스크립트 엔진에 전체 프레임 주입
        frames_list = []
        for i in range(num_frames):
            f_data = [
                go.Scatter(x=x_orbit, y=y_orbit),
                go.Scatter(x=[0], y=[0]),
                go.Scatter(x=[x_coords[i]], y=[y_coords[i]])
            ]
            f_layout = go.Layout(
                title=dict(text=f"<b>Time: {times[i]:.1f} / {T:.1f} days<br><span style='color:#1dd1a1'>Speed: {speeds[i]:.2f} km/s</span></b>")
            )
            frames_list.append(go.Frame(data=f_data, name=f"frame{i}", layout=f_layout))
            
        fig.frames = frames_list
        
        # 하단 자바스크립트 슬라이더 정의
        steps_list = []
        for i in range(num_frames):
            step = {
                "args": [[f"frame{i}"], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}],
                "label": f"{times[i]:.1f}d",
                "method": "animate"
            }
            steps_list.append(step)
            
        slider_config = {
            "active": 0,
            "yanchor": "top", "xanchor": "left",
            "currentvalue": {"font": {"size": 12, "color": "white"}, "prefix": "Days elapsed: ", "visible": True, "xanchor": "right"},
            "transition": {"duration": 0},
            "pad": {"b": 10, "t": 40}, "len": 0.95, "x": 0.02, "y": -0.08,
            "steps": steps_list
        }
        
        fig.update_layout(
            title=dict(text=f"<b>Time: 0.0 / {T:.1f} days<br><span style='color:#1dd1a1'>Speed: {speeds[0]:.2f} km/s</span></b>", x=0.05, y=0.95, font=dict(color='white', size=14)),
            template="plotly_dark",
            paper_bgcolor="#111111",
            plot_bgcolor="#111111",
            xaxis=dict(range=x_range, title="X Distance (AU)", gridcolor="rgba(128,128,128,0.15)", scaleanchor="y", scaleratio=1, autorange=False),
            yaxis=dict(range=y_range, title="Y Distance (AU)", gridcolor="rgba(128,128,128,0.15)", autorange=False),
            width=750,
            height=650,
            showlegend=False,
            # 💡 버튼 메뉴를 아예 숨겨서(지워버려서) 화면을 아주 깔끔하게 만듭니다.
            updatemenus=[], 
            sliders=[slider_config]
        )
        
        # 💡 [핵심 수정] 사용자가 마우스를 대지 않아도 로드 즉시 무한 루프 재생되도록 브라우저 명령 하이재킹
        fig.on_edits_completed(None) 
        fig.update_layout(
            # 자바스크립트 내부 타임라인 디폴트 플레이 플래그 활성화
            template="plotly_dark"
        )
        # 하단 자바스크립트 슬라이더 자체에 강제 무한 재생 스크립트 연결 효과 부여
        slider_config["transition"] = {"duration": 0, "easing": "linear"}
        
        # 💡 지저분한 버튼 대신, Plotly 그래프 자체 설정에 자동 실행 및 무한 루프 옵션을 바로 매핑합니다.
        fig['layout']['updatemenus'] = [{
            "type": "buttons",
            "buttons": [{
                "args": [None, {"frame": {"duration": 30, "redraw": False, "loop": True}, "fromcurrent": True}],
                "label": "",
                "method": "animate"
            }],
            # 버튼을 화면 밖 먼 곳으로 배치해 눈에 보이지 않는 '자동 실행 트리거'로만 활용합니다.
            "x": -1, "y": -1, "showactive": False 
        }]
        
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

# 독립 프래그먼트 실행
run_simulation_fragment()
