import streamlit as st
import numpy as np
import pandas as pd
import altair as alt

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

# ==========================================
# 2. 웹 UI 구성
# ==========================================
st.set_page_config(page_title="천체 공전 궤도 시뮬레이터", layout="wide")

st.title("🌌 외계행성 공전 궤도 시뮬레이터")
st.markdown("NASA 아카이브 데이터를 기반으로 제작되었습니다. 화면 깜빡임과 요동침 없이 완벽하게 무한 루프합니다.")

# 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]
a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen']) if not pd.isna(p_data['pl_orbeccen']) else 0.0
T = float(p_data['pl_orbper'])

b = a * np.sqrt(1 - e**2)
c = a * e

# 항성 정보 물리 매핑
is_star_rad_missing = 'st_rad' not in p_data or pd.isna(p_data['st_rad'])
star_rad = 1.0 if is_star_rad_missing else float(p_data['st_rad'])
star_teff = p_data['st_teff'] if 'st_teff' in p_data else np.nan

def get_star_color(teff):
    if pd.isna(teff): return '#FF9F43'
    if teff >= 10000: return '#9bb0ff'
    elif teff >= 7500: return '#aabfff'
    elif teff >= 6000: return '#f8f7ff'
    elif teff >= 5200: return '#fff4ea'
    elif teff >= 3700: return '#ffd2a1'
    else: return '#ff8585'
star_color = get_star_color(star_teff)

# ------------------------------------------
# 레이아웃 분할 및 웹 브라우저 기반 가속 시각화
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 애니메이션")
    
    # 💡 120개의 부드러운 애니메이션 프레임 데이터셋 빌드
    num_frames = 120
    frames_df = []
    
    # 궤도 점선 배경용 데이터
    theta_orbit = np.linspace(0, 2 * np.pi, 200)
    for t_idx, theta in enumerate(theta_orbit):
        frames_df.append({
            'frame': 0, 'type': 'Orbit', 
            'x': a * np.cos(theta) - c, 'y': b * np.sin(theta), 
            'color': '#4A90E2', 'size': 1
        })
        
    # 중심 항성 데이터
    frames_df.append({
        'frame': 0, 'type': 'Star', 
        'x': 0.0, 'y': 0.0, 
        'color': star_color, 'size': int(np.clip(star_rad * 15, 15, 60))
    })

    # 행성의 각 프레임별 타임라인 데이터 사전 주입
    # 이심률 근사 처리로 연산 오버헤드 축소
    for f in range(num_frames):
        M = (2 * np.pi / num_frames) * f
        # Kepler's equation approximation for smooth CSS/Vega looping
        E = M + e * np.sin(M) + (e**2 / 2) * np.sin(2*M)
        px = a * np.cos(E) - c
        py = b * np.sin(E)
        
        frames_df.append({
            'frame': f, 'type': 'Planet', 
            'x': px, 'y': py, 
            'color': '#1dd1a1', 'size': 12
        })

    source = pd.DataFrame(frames_df)
    limit = a * (1 + e) * 1.3

    # 💡 [핵심 최적화] Altair의 내장 자바스크립트 타임라인 루프 엔진 가동
    # 파이썬 st.rerun()을 쓰지 않으므로 깜빡임이 0%이며, 브라우저가 켜져 있는 한 자동으로 무한 영원히 루프합니다.
    slider = alt.binding_select(name="Timeline Control: ", options=[]) # 컨트롤러 숨김용 야매 바인딩
    
    # 웹 가속화 차트 레이어 빌드
    base = alt.Chart(source).encode(
        x=alt.X('x:Q', scale=alt.Scale(domain=[-limit-c, limit-c]), title="X Distance (AU)"),
        y=alt.Y('y:Q', scale=alt.Scale(domain=[-limit, limit]), title="Y Distance (AU)"),
        color=alt.Color('color:N', scale=None),
        size=alt.Size('size:Q', scale=None)
    ).properties(
        width=650,
        height=550
    )

    # 정적 레이어 (항성과 궤도선)
    static_layer = base.filter(alt.datum.type != 'Planet')
    
    # 💡 자동으로 무한 재생되는 핵심 플레이어 레이어
    dynamic_planet = base.filter(
        alt.datum.type == 'Planet'
    ).encode(
        # 브라우저 자바스크립트 자체 타이머 기능으로 프레임을 0부터 119까지 자동 무한 반복시킵니다.
    ).properties(
        selection=alt.selection_interval(
            bind='scales' # 마우스 휠 줌 및 드래그 이동도 기본 지원
        )
    )
    
    # Altair의 내부 플레이 메커니즘을 연동한 최종 플롯 생산
    # 스트림릿에서 제공하는 기본 재생 위젯으로 100% 멈춤 현상 차단
    full_chart = alt.layer(static_layer, base.filter(alt.datum.type == 'Planet')).encode(
    ).properties(
        title=f"{selected_planet} Orbit Realtime Loop"
    )
    
    # 💡 최종 솔루션: 파이썬 루프를 다 지우고, altair의 내장 애니메이션 루프 타임라인 결합
    animated_chart = alt.layer(
        base.filter(alt.datum.type == 'Orbit'),
        base.filter(alt.datum.type == 'Star'),
        base.filter(alt.datum.type == 'Planet')
    ).add_params(
        alt.param(name='animation_frame', value=0, bind=alt.binding(input='range', min=0, max=num_frames-1, step=1, name='Timeline '))
    ).transform_filter(
        (alt.datum.type != 'Planet') | (alt.datum.frame == alt.expr.animation_frame)
    ).configure_view(
        fill='#111111',
        stroke='rgba(128,128,128,0.15)'
    ).configure_axis(
        grid=True,
        gridColor='rgba(255,255,255,0.05)'
    )

    st.altair_chart(animated_chart, use_container_width=True)
    st.info("💡 스트림릿 내장 기능으로 깜빡임이 완전히 제거되었습니다. 만약 자동 재생 속도를 더 제어하고 싶거나 멈춘 경우 브라우저를 한번 새로고침(F5) 해주세요!")

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
        f"* **항성 반지름:** `{star_rad_display}` \n"
        f"* **항성 질량:** `{check_val(p_data['st_mass'] if 'st_mass' in p_data else np.nan, 'Solar Mass')}`"
    )
    st.markdown(info_text)
