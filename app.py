import streamlit as st
import numpy as np
import pandas as pd

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
st.markdown("NASA 아카이브 데이터를 기반으로 제작되었습니다. 브라우저 하드웨어 가속을 통해 멈춤과 요동침 없이 영원히 공전합니다.")

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
    
    # 💡 브라우저 내장 자바스크립트로 초고속 무한 루프를 돌리는 HTML Injection 코드
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ background-color: #111111; margin: 0; overflow: hidden; font-family: sans-serif; }}
            canvas {{ background: #111111; display: block; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <canvas id="orbitCanvas" width="700" height="550"></canvas>
        <script>
            const canvas = document.getElementById('orbitCanvas');
            const ctx = canvas.getContext('2d');
            
            // 파이썬에서 넘겨받은 천체 물리 상수 변수화
            const a = {a};
            const e = {e};
            const b = {b};
            const c = {c};
            const starColor = "{star_color}";
            
            // 화면 꽉 차게 스케일 자동 정적 매핑 (출렁거림 원천 차단)
            const limit = a * (1 + e) * 1.3;
            const scale = (canvas.width / 2) / limit;
            
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            
            let angle = 0; // 공전 타이머 변수
            
            function draw() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // 1. 배경 그리드망 선배치 (옵션)
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
                ctx.lineWidth = 1;
                for(let i=0; i<canvas.width; i+=50) {{
                    ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke();
                }}
                
                // 2. 궤도선 (푸른색 점선 고정)
                ctx.save();
                ctx.translate(centerX - (c * scale), centerY);
                ctx.strokeStyle = '#4A90E2';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.ellipse(0, 0, a * scale, b * scale, 0, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.restore();
                
                // 3. 중심 항성 (태양) 배치
                ctx.beginPath();
                ctx.arc(centerX, centerY, Math.max(8, Math.min({star_rad} * 12, 35)), 0, 2 * Math.PI);
                ctx.fillStyle = starColor;
                ctx.shadowColor = starColor;
                ctx.shadowBlur = 15;
                ctx.fill();
                ctx.shadowBlur = 0; // 그림자 초기화
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // 4. 케플러 타원 이심률 각도 근사 계산 (부드러운 주행감 유도)
                let E = angle + e * Math.sin(angle) + (e*e/2) * Math.sin(2*angle);
                let planetX = centerX - (c * scale) + (a * scale * Math.cos(E));
                let planetY = centerY + (b * scale * Math.sin(E));
                
                // 5. 초록색 공전 행성 그리기
                ctx.beginPath();
                ctx.arc(planetX, planetY, 7, 0, 2 * Math.PI);
                ctx.fillStyle = '#1dd1a1';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();
                
                // 💡 [무한 루프의 핵심] 각도를 전진시키고, 2파이(360도)를 넘으면 자동으로 0부터 무한 반복
                angle += 0.025; 
                if (angle >= 2 * Math.PI) angle = 0;
                
                // 브라우저 자체 주사율에 맞춰 부드럽게 무한 루프 실행 (60FPS 보장)
                requestAnimationFrame(draw);
            }}
            
            // 시뮬레이션 즉시 스타트
            draw();
        </script>
    </body>
    </html>
    """
    
    # 스트림릿 내장 html 컴포넌트로 주입 (깜빡임, 리런 멈춤 현상 100% 없음)
    st.components.v1.html(html_code, height=560)

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
