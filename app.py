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
st.set_page_config(page_title="행성 공전 궤도 시뮬레이터", layout="wide")

st.title("행성 공전 궤도 시뮬레이터")
st.markdown("NASA Exoplanet Archive를 기반으로 제작되었습니다.")

# ⚙️ 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names)

show_earth_orbit = st.sidebar.checkbox("🌍 지구 궤도 비교선 표시", value=False)
show_habitable_zone = st.sidebar.checkbox("🟢 골디락스 존 표시", value=False)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]
a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen']) if not pd.isna(p_data['pl_orbeccen']) else 0.0
T = float(p_data['pl_orbper'])

b = a * np.sqrt(1 - e**2)
c = a * e
mu = (4 * np.pi**2 * (a**3)) / (T**2) if T > 0 else 1.0

# 항성 정보 및 골디락스 존(HZ) 범위 연산
is_star_rad_missing = 'st_rad' not in p_data or pd.isna(p_data['st_rad'])
star_rad = 1.0 if is_star_rad_missing else float(p_data['st_rad'])
star_teff = p_data['st_teff'] if 'st_teff' in p_data else np.nan

star_mass = float(p_data['st_mass']) if 'st_mass' in p_data and not pd.isna(p_data['st_mass']) else 1.0
hz_inner = 0.75 * np.sqrt(star_mass)
hz_outer = 1.77 * np.sqrt(star_mass)

# 💡 표면온도에 따른 색상 및 분광형 계산 함수
def get_star_info(teff):
    if pd.isna(teff): 
        return '#FF9F43', '정보 없음'
    if teff >= 10000: 
        return '#9bb0ff', 'O형 또는 B형 (청백색)'
    elif teff >= 7500: 
        return '#aabfff', 'A형 (백색)'
    elif teff >= 6000: 
        return '#f8f7ff', 'F형 (황백색)'
    elif teff >= 5200: 
        return '#fff4ea', 'G형 (황색)'
    elif teff >= 3700: 
        return '#ffd2a1', 'K형 (주황색)'
    else: 
        return '#ff8585', 'M형 (적색)'

star_color, star_spectral_type = get_star_info(star_teff)

# ------------------------------------------
# 레이아웃 분할 및 시각화
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 애니메이션")
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background-color: #111111; margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white; }}
            #container {{ position: relative; width: 100%; max-width: 700px; margin: 0 auto; background: #111111; }}
            canvas {{ background: #111111; display: block; width: 100%; height: auto; }}
            
            #infoOverlay {{ position: absolute; top: 15px; left: 20px; font-size: 14px; font-weight: bold; line-height: 1.5; pointer-events: none; z-index: 10; }}
            #speedText {{ color: #1dd1a1; }}
            
            #mainControls {{
                background: #1a1a1a; padding: 15px; border-radius: 8px; margin-top: 10px;
                display: flex; flex-direction: column; gap: 12px; border: 1px solid #333;
            }}
            .row {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: center; }}
            
            .uiBtn {{ 
                background: #111111; border: 1px solid #555555; color: white; 
                padding: 6px 14px; font-size: 13px; font-weight: bold; border-radius: 4px; cursor: pointer; 
                transition: all 0.2s;
            }}
            .uiBtn:hover {{ background: #222222; border-color: #1dd1a1; color: #1dd1a1; }}
            .activeSpeed {{ background: #1dd1a1 !important; color: #111111 !important; border-color: #1dd1a1 !important; }}
            
            .sliderContainer {{ display: flex; align-items: center; gap: 10px; font-size: 13px; flex-grow: 1; }}
            .sliderContainer input {{ flex-grow: 1; cursor: pointer; accent-color: #1dd1a1; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="infoOverlay">
                <div id="timeText">Time: 0.0 / {T:.1f} days</div>
                <div id="speedText">Speed: 0.00 km/s</div>
            </div>
            <canvas id="orbitCanvas" width="700" height="530"></canvas>
        </div>

        <div id="mainControls">
            <div class="row">
                <button id="controlBtn" class="uiBtn">⏸ Pause</button>
                <button id="speed05" class="uiBtn">0.5x</button>
                <button id="speed10" class="uiBtn activeSpeed">1.0x</button>
                <button id="speed20" class="uiBtn">2.0x</button>
            </div>
            
            <div class="row">
                <div class="sliderContainer">
                    <span>🔍 줌 조절:</span>
                    <input type="range" id="zoomSlider" min="0.1" max="3.0" step="0.1" value="1.0">
                    <span id="zoomVal">1.0x</span>
                </div>
            </div>
        </div>

        <script>
            const canvas = document.getElementById('orbitCanvas');
            const ctx = canvas.getContext('2d');
            const timeLabel = document.getElementById('timeText');
            const speedLabel = document.getElementById('speedText');
            
            const controlBtn = document.getElementById('controlBtn');
            const btn05 = document.getElementById('speed05');
            const btn10 = document.getElementById('speed10');
            const btn20 = document.getElementById('speed20');
            const zoomSlider = document.getElementById('zoomSlider');
            const zoomVal = document.getElementById('zoomVal');
            
            const a = {a};
            const e = {e};
            const b = {b};
            const c = {c};
            const T = {T};
            const mu = {mu};
            const starColor = "{star_color}";
            
            const showEarthOrbit = {str(show_earth_orbit).lower()};
            const showHabitableZone = {str(show_habitable_zone).lower()};
            
            const hzInner = {hz_inner};
            const hzOuter = {hz_outer};
            
            const earthA = 1.0;
            const earthE = 0.0167;
            const earthB = earthA * Math.sqrt(1 - Math.pow(earthE, 2));
            const earthC = earthA * earthE;
            
            const paddingLeft = 70;
            const paddingRight = 40;
            const paddingTop = 40;
            const paddingBottom = 40;
            
            const plotWidth = canvas.width - (paddingLeft + paddingRight);
            const plotHeight = canvas.height - (paddingTop + paddingBottom);
            
            const baseLimit = (a + c) * 1.3;
            
            let currentDays = 0;
            let isPlaying = true;
            let speedMultiplier = 1.0;
            let currentZoom = 1.0;
            
            controlBtn.addEventListener('click', () => {{
                isPlaying = !isPlaying;
                controlBtn.textContent = isPlaying ? "⏸ Pause" : "▶ Play";
                if (isPlaying) draw();
            }});
            
            function updateSpeedSelection(activeBtn, targetMultiplier) {{
                btn05.classList.remove('activeSpeed');
                btn10.classList.remove('activeSpeed');
                btn20.classList.remove('activeSpeed');
                activeBtn.classList.add('activeSpeed');
                speedMultiplier = targetMultiplier;
            }}
            
            btn05.addEventListener('click', () => updateSpeedSelection(btn05, 0.5));
            btn10.addEventListener('click', () => updateSpeedSelection(btn10, 1.0));
            btn20.addEventListener('click', () => updateSpeedSelection(btn20, 2.0));
            
            zoomSlider.addEventListener('input', (e) => {{
                currentZoom = parseFloat(e.target.value);
                zoomVal.textContent = currentZoom.toFixed(1) + "x";
            }});

            function draw() {{
                if (!isPlaying) return;

                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                let limit = baseLimit / currentZoom;
                let scale = Math.min(plotWidth, plotHeight) / (2 * limit);
                
                let centerX = paddingLeft + (plotWidth / 2) - (plotWidth * 0.15);
                let centerY = paddingTop + (plotHeight / 2);
                
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

                if (showHabitableZone) {{
                    ctx.save();
                    ctx.translate(centerX, centerY);
                    ctx.fillStyle = 'rgba(29, 209, 161, 0.08)';
                    ctx.strokeStyle = 'rgba(29, 209, 161, 0.25)';
                    ctx.lineWidth = 1;
                    
                    ctx.beginPath();
                    ctx.arc(0, 0, hzOuter * scale, 0, 2 * Math.PI, false);
                    ctx.arc(0, 0, hzInner * scale, 0, 2 * Math.PI, true);
                    ctx.fill();
                    
                    ctx.beginPath();
                    ctx.arc(0, 0, hzOuter * scale, 0, 2 * Math.PI);
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.arc(0, 0, hzInner * scale, 0, 2 * Math.PI);
                    ctx.stroke();
                    
                    ctx.fillStyle = 'rgba(29, 209, 161, 0.5)';
                    ctx.font = "italic 11px 'Segoe UI'";
                    ctx.textAlign = "left";
                    ctx.fillText("Habitable Zone", hzInner * scale + 5, -5);
                    ctx.restore();
                }}

                if (showEarthOrbit) {{
                    ctx.save();
                    ctx.translate(centerX + (earthC * scale), centerY);
                    ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
                    ctx.lineWidth = 1.2;
                    ctx.setLineDash([3, 6]);
                    ctx.beginPath();
                    ctx.ellipse(0, 0, earthA * scale, earthB * scale, 0, 0, 2 * Math.PI);
                    ctx.stroke();
                    
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
                    ctx.font = "italic 11px 'Segoe UI'";
                    ctx.textAlign = "right";
                    ctx.fillText("Earth Orbit (1.0 AU)", -(earthA + earthC) * scale - 5, 0);
                    ctx.restore();
                }}

                ctx.save();
                ctx.translate(centerX + (c * scale), centerY);
                ctx.strokeStyle = '#4A90E2';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.ellipse(0, 0, a * scale, b * scale, 0, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.restore();
                
                ctx.beginPath();
let calculatedStarRad = {star_rad} * 12 * currentZoom; // 기본 크기 배율을 10에서 12로 살짝 키워 시각 효과 업!
let finalStarRad = Math.max(5, calculatedStarRad);    // 너무 축소해서 별이 사라지는 것만 방지 (최소 5픽셀)

ctx.arc(centerX, centerY, finalStarRad, 0, 2 * Math.PI);
                ctx.fillStyle = starColor;
                ctx.shadowColor = starColor;
                ctx.shadowBlur = 12;
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                let M_val = (2 * Math.PI / T) * currentDays;
                let E = M_val + e * Math.sin(M_val) + (e*e/2) * Math.sin(2*M_val);
                
                let planetX = centerX + (c * scale) + (a * scale * Math.cos(E));
                let planetY = centerY + (b * scale * Math.sin(E));
                
                ctx.beginPath();
                ctx.arc(planetX, planetY, 6, 0, 2 * Math.PI);
                ctx.fillStyle = '#1dd1a1';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();
                
                let r_p = Math.sqrt(Math.pow((planetX - centerX)/scale, 2) + Math.pow((planetY - centerY)/scale, 2));
                let v_kms = 0;
                if (r_p > 0 && (2/r_p - 1/a) > 0) {{
                    let v_au = Math.sqrt(mu * (2/r_p - 1/a));
                    v_kms = v_au * 149597870.7 / 86400;
                }}
                
                timeLabel.innerHTML = `<b>Time: ${{currentDays.toFixed(1)}} / ${{T.toFixed(1)}} days</b>`;
                speedLabel.innerHTML = `<b>Speed: ${{v_kms.toFixed(2)}} km/s</b>`;
                
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
    
    st.components.v1.html(html_code, height=660)

with col2:
    st.subheader("📊 데이터")
    def check_val(val, unit=""): return f"{val:.3f} {unit}" if not pd.isna(val) else "정보 없음"
    star_rad_display = "정보 없음 (기본값)" if is_star_rad_missing else f"{star_rad:.3f} Solar Rad"
    star_teff_display = f"{star_teff:.1f} K" if not pd.isna(star_teff) else "정보 없음"
    
    info_text = (
        f"### 🪐 행성 궤도 정보\n"
        f"* **이름:** `{p_data['pl_name']}`\n"
        f"* **공전 주기:** `{T:.1f} 일` \n"
        f"* **궤도 장반경:** `{a:.3f} AU` \n"
        f"* **궤도 이심률:** `{e:.3f}` \n\n"
        f"### ☀️ 중심 항성 정보\n"
        f"* **항성 반지름:** `{star_rad_display}` \n"
        f"* **항성 질량:** `{check_val(p_data['st_mass'] if 'st_mass' in p_data else np.nan, 'Solar Mass')}`\n"
        f"* **항성 표면온도:** `{star_teff_display}`\n"
        f"* **항성 분광형:** ` {star_spectral_type} `" # 💡 분광형 정보 출력 코드 추가
    )
    st.markdown(info_text)
