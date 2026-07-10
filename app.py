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
st.markdown("NASA 아카이브 데이터를 기반으로 제작되었습니다. 배속 조절 버튼을 사용하여 공전 속도를 제어할 수 있습니다.")

# 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names)

# 💡 [2번 기능 추가] 공전 속도 배속 선택 버튼 (라디오 버튼 스타일)
speed_option = st.sidebar.radio(
    "⏱️ 공전 속도 배속 조절",
    options=["0.5x (느리게)", "1.0x (정속)", "2.0x (빠르게)"],
    index=1  # 기본값: 1.0x (정속)
)
# 문자열에서 숫자 배속 값만 추출 (0.5, 1.0, 2.0)
speed_multiplier = float(speed_option.split("x")[0])

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
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ background-color: #111111; margin: 0; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white; }}
            #container {{ position: relative; width: 700px; height: 580px; margin: 0 auto; }}
            canvas {{ background: #111111; display: block; }}
            #infoOverlay {{ position: absolute; top: 15px; left: 20px; font-size: 15px; font-weight: bold; line-height: 1.5; pointer-events: none; z-index: 10; }}
            #speedText {{ color: #1dd1a1; }}
            #controlBtn {{ 
                position: absolute; bottom: 25px; left: 70px; 
                background: #111111; border: 1px solid #555555; color: white; 
                padding: 6px 12px; font-size: 13px; font-weight: bold; border-radius: 4px; cursor: pointer; 
                transition: all 0.2s; z-index: 10;
            }}
            #controlBtn:hover {{ background: #222222; border-color: #1dd1a1; color: #1dd1a1; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="infoOverlay">
                <div id="timeText">Time: 0.0 / {T:.1f} days</div>
                <div id="speedText">Speed: 0.00 km/s</div>
            </div>
            <button id="controlBtn">⏸ Pause</button>
            <canvas id="orbitCanvas" width="700" height="580"></canvas>
        </div>

        <script>
            const canvas = document.getElementById('orbitCanvas');
            const ctx = canvas.getContext('2d');
            const timeLabel = document.getElementById('timeText');
            const speedLabel = document.getElementById('speedText');
            const controlBtn = document.getElementById('controlBtn');
            
            const a = {a};
            const e = {e};
            const b = {b};
            const c = {c};
            const T = {T};
            const mu = {mu};
            const starColor = "{star_color}";
            
            // 스트림릿에서 전달받은 배속Multiplier 값 적용
            const speedMultiplier = {speedMultiplier};
            
            const paddingLeft = 70;
            const paddingRight = 40;
            const paddingTop = 40;
            const paddingBottom = 60;
            
            const plotWidth = canvas.width - (paddingLeft + paddingRight);
            const plotHeight = canvas.height - (paddingTop + paddingBottom);
            
            const limit = (a + c) * 1.3;
            const scale = Math.min(plotWidth, plotHeight) / (2 * limit);
            
            // 항성 중심을 기준으로 왼쪽 시프트
            const centerX = paddingLeft + (plotWidth / 2) - (plotWidth * 0.15);
            const centerY = paddingTop + (plotHeight / 2);
            
            let currentDays = 0;
            let isPlaying = true;
            
            controlBtn.addEventListener('click', () => {{
                isPlaying = !isPlaying;
                controlBtn.textContent = isPlaying ? "⏸ Pause" : "▶ Play";
                if (isPlaying) draw();
            }});

            function draw() {{
                if (!isPlaying) return;

                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // 1. 축 가이드 라인 및 숫자 눈금 그리기
                ctx.lineWidth = 1;
                ctx.font = "11px 'Segoe UI'";
                
                let stepAU = 1;
                if (limit > 3) stepAU = 1;
                if (limit > 8) stepAU = 2;
                if (limit > 20) stepAU = 5;
                if (limit > 50) stepAU = 10;
                if (limit > 150) stepAU = 50;
                if (limit > 600) stepAU = 200;
                if (limit < 1) stepAU = 0.2;
                if (limit < 0.3) stepAU = 0.05;

                // X축 눈금선
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                for (let xAU = -Math.floor(limit*2/stepAU)*stepAU; xAU <= limit * 2; xAU += stepAU) {{
                    let canvasX = centerX + (xAU * scale);
                    if (canvasX >= paddingLeft && canvasX <= paddingLeft + plotWidth) {{
                        ctx.strokeStyle = Math.abs(xAU) < 0.001 ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.03)';
                        ctx.beginPath(); ctx.moveTo(canvasX, paddingTop); ctx.lineTo(canvasX, paddingTop + plotHeight); ctx.stroke();
                        
                        ctx.fillStyle = '#888888';
                        let decimals = stepAU < 1 ? (stepAU < 0.1 ? 2 : 1) : 0;
                        ctx.fillText(xAU.toFixed(decimals) + " AU", canvasX, paddingTop + plotHeight + 6);
                    }}
                }}
                
                // Y축 눈금선
                ctx.textAlign = "right";
                ctx.textBaseline = "middle";
                for (let yAU = -Math.floor(limit*2/stepAU)*stepAU; yAU <= limit * 2; yAU += stepAU) {{
                    let canvasY = centerY - (yAU * scale);
                    if (canvasY >= paddingTop && canvasY <= paddingTop + plotHeight) {{
                        ctx.strokeStyle = Math.abs(yAU) < 0.001 ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.03)';
                        ctx.beginPath(); ctx.moveTo(paddingLeft, canvasY); ctx.lineTo(paddingLeft + plotWidth, canvasY); ctx.stroke();
                        
                        ctx.fillStyle = '#888888';
                        let decimals = stepAU < 1 ? (stepAU < 0.1 ? 2 : 1) : 0;
                        ctx.fillText(yAU.toFixed(decimals) + " AU", paddingLeft - 8, canvasY);
                    }}
                }}

                ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
                ctx.strokeRect(paddingLeft, paddingTop, plotWidth, plotHeight);

                // 2. 푸른색 공전 궤도선
                ctx.save();
                ctx.translate(centerX + (c * scale), centerY);
                ctx.strokeStyle = '#4A90E2';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.ellipse(0, 0, a * scale, b * scale, 0, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.restore();
                
                // 3. 중심 항성 (태양)
                ctx.beginPath();
                ctx.arc(centerX, centerY, Math.max(6, Math.min({star_rad} * 10, 28)), 0, 2 * Math.PI);
                ctx.fillStyle = starColor;
                ctx.shadowColor = starColor;
                ctx.shadowBlur = 12;
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // 4. 행성 위치 연산
                let M_val = (2 * Math.PI / T) * currentDays;
                let E = M_val + e * Math.sin(M_val) + (e*e/2) * Math.sin(2*M_val);
                
                let planetX = centerX + (c * scale) + (a * scale * Math.cos(E));
                let planetY = centerY + (b * scale * Math.sin(E));
                
                // 5. 초록색 외계행성
                ctx.beginPath();
                ctx.arc(planetX, planetY, 6, 0, 2 * Math.PI);
                ctx.fillStyle = '#1dd1a1';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();
                
                // 6. 실시간 데이터 업데이트
                let r_p = Math.sqrt(Math.pow((planetX - centerX)/scale, 2) + Math.pow((planetY - centerY)/scale, 2));
                let v_kms = 0;
                if (r_p > 0 && (2/r_p - 1/a) > 0) {{
                    let v_au = Math.sqrt(mu * (2/r_p - 1/a));
                    v_kms = v_au * 149597870.7 / 86400;
                }}
                
                timeLabel.innerHTML = `<b>Time: ${{currentDays.toFixed(1)}} / ${{T.toFixed(1)}} days</b>`;
                speedLabel.innerHTML = `<b>Speed: ${{v_kms.toFixed(2)}} km/s</b>`;
                
                // 7. 프레임 전진
                // 💡 [2번 기능 포인트] 기존 하루 변화량(dt)에 유저가 선택한 speedMultiplier 배속을 곱해줍니다.
                let dt = (T / 350) * speedMultiplier; 
                currentDays += dt;
                if (currentDays >= T) currentDays = 0;
                
                requestAnimationFrame(draw);
            }}
            
            draw();
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=590)

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
