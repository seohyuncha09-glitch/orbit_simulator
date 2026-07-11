import streamlit as st
import numpy as np
import pandas as pd

# ==========================================
# 1. 데이터 불러오기
# ==========================================
@st.cache_data
def load_data():
    return pd.read_csv("PS_data_updated.csv")

try:
    df = load_data()
    all_planet_names = sorted(df['pl_name'].dropna().unique())
except Exception as e:
    st.error("CSV 파일을 찾을 수 없습니다. GitHub 저장소에 'PS_data_updated.csv' 파일이 있는지 확인해 주세요.")
    st.stop()

# ==========================================
# 2. 웹 UI 구성
# ==========================================
st.set_page_config(page_title="행성 공전 궤도 시뮬레이터 (True Scale)", layout="wide")

st.title("행성 공전 궤도 시뮬레이터")
st.markdown("NASA Exoplanet Archive를 기반으로 제작되었습니다.")

# ⚙️ 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")

selected_planet = st.sidebar.selectbox(
    "🪐 탐색할 행성 선택", 
    all_planet_names, 
    key="sidebar_planet_selector"
)

st.sidebar.markdown("---")
show_earth_orbit = st.sidebar.checkbox("🌍 지구 궤도 비교선 표시", value=False)
show_habitable_zone = st.sidebar.checkbox("🟢 골디락스 존 표시", value=False)

# 🎯 깔끔한 십자 조준선 제어
highlight_planet = st.sidebar.checkbox("🎯 행성 강조선 표시", value=True)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]
a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen']) if not pd.isna(p_data['pl_orbeccen']) else 0.0
T = float(p_data['pl_orbper'])

# 행성 반지름(지구 대비) 데이터 추출
is_pl_rade_missing = 'pl_rade' not in p_data or pd.isna(p_data['pl_rade'])
pl_rade = 1.0 if is_pl_rade_missing else float(p_data['pl_rade'])

b = a * np.sqrt(1 - e**2)
c = a * e
mu = (4 * np.pi**2 * (a**3)) / (T**2) if T > 0 else 1.0

# 항성 정보 및 분광형 추출
is_star_rad_missing = 'st_rad' not in p_data or pd.isna(p_data['st_rad'])
star_rad = 1.0 if is_star_rad_missing else float(p_data['st_rad'])
star_teff = p_data['st_teff'] if 'st_teff' in p_data else np.nan

# 파일의 st_spectype 항목값 가져오기
star_spectral_type = p_data['st_spectype'] if 'st_spectype' in p_data and not pd.isna(p_data['st_spectype']) else "정보 없음"

star_mass = float(p_data['st_mass']) if 'st_mass' in p_data and not pd.isna(p_data['st_mass']) else 1.0
hz_inner = 0.953 * np.sqrt(star_mass)
hz_outer = 1.373 * np.sqrt(star_mass)

# 분광형 데이터(st_spectype) 첫 글자 기반 색상 지정 함수
def get_star_color_by_spectype(spectype, teff):
    if spectype and spectype != "정보 없음":
        first_char = str(spectype).strip().upper()[0]
        if first_char in ['O', 'B']: return '#9bb0ff'
        elif first_char == 'A': return '#aabfff'
        elif first_char == 'F': return '#f8f7ff'
        elif first_char == 'G': return '#fff4ea'
        elif first_char == 'K': return '#ffd2a1'
        elif first_char == 'M': return '#ff8585'
    
    # 분광형 정보가 비어있거나 불명확할 경우 표면온도로 폴백
    if pd.isna(teff): return '#FF9F43'
    if teff >= 10000: return '#9bb0ff'
    elif teff >= 7500: return '#aabfff'
    elif teff >= 6000: return '#f8f7ff'
    elif teff >= 5200: return '#fff4ea'
    elif teff >= 3700: return '#ffd2a1'
    else: return '#ff8585'

star_color = get_star_color_by_spectype(star_spectral_type, star_teff)

# ------------------------------------------
# 레이아웃 분할 및 시각화
# ------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"✨ {selected_planet} 궤도 시뮬레이션")
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ background-color: #111111; margin: 0; font-family: 'Segoe UI', sans-serif; color: white; }}
            #container {{ position: relative; width: 100%; max-width: 700px; margin: 0 auto; background: #111111; }}
            canvas {{ background: #111111; display: block; width: 100%; height: auto; }}
            
            #infoOverlay {{ position: absolute; top: 15px; left: 20px; font-size: 14px; font-weight: bold; line-height: 1.5; pointer-events: none; z-index: 10; }}
            #speedText {{ color: #1dd1a1; }}
            
            #mainControls {{
                background: #1a1a1a; padding: 15px; border-radius: 8px; margin-top: 10px;
                display: flex; flex-direction: column; gap: 12px; border: 1px solid #333;
            }}
            .row {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: center; justify-content: space-between; }}
            
            .uiBtn {{ 
                background: #111111; border: 1px solid #555555; color: white; 
                padding: 6px 14px; font-size: 13px; font-weight: bold; border-radius: 4px; cursor: pointer; transition: all 0.2s;
            }}
            .uiBtn:hover {{ background: #222222; border-color: #1dd1a1; color: #1dd1a1; }}
            .activeSpeed {{ background: #1dd1a1 !important; color: #111111 !important; border-color: #1dd1a1 !important; }}
            
            .sliderContainer {{ display: flex; align-items: center; gap: 10px; font-size: 13px; flex-grow: 1; }}
            .sliderContainer input {{ flex-grow: 1; cursor: pointer; accent-color: #1dd1a1; }}
            
            .checkboxContainer {{ display: flex; align-items: center; gap: 5px; font-size: 14px; font-weight: bold; color: #4a90e2; cursor: pointer; }}
            .checkboxContainer input {{ cursor: pointer; transform: scale(1.2); accent-color: #4a90e2; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="infoOverlay">
                <div id="timeText">Time: 0.0 / {T:.1f} days</div>
                <div id="speedText">Speed: 0.00 km/s</div>
            </div>
            <canvas id="orbitCanvas" width="700" height="520"></canvas>
        </div>

        <div id="mainControls">
            <div class="row">
                <div style="display: flex; gap: 10px;">
                    <button id="controlBtn" class="uiBtn">⏸ Pause</button>
                    <button id="speed05" class="uiBtn">0.5x</button>
                    <button id="speed10" class="uiBtn activeSpeed">1.0x</button>
                    <button id="speed20" class="uiBtn">2.0x</button>
                </div>
                <label class="checkboxContainer">
                    <input type="checkbox" id="followPlanet"> 행성 추적
                </label>
            </div>
            
            <div class="row">
                <div class="sliderContainer">
                    <span>확대/축소:</span>
                    <input type="range" id="zoomSlider" min="-1" max="5.5" step="0.1" value="0">
                    <span id="zoomVal" style="width: 50px; text-align: right;">1x</span>
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
            const followPlanetCb = document.getElementById('followPlanet');
            
            const SOLAR_RAD_TO_AU = 0.00465047;
            const EARTH_RAD_TO_AU = 0.000042635;
            
            const a = {a};
            const e = {e};
            const b = {b};
            const c = {c};
            const T = {T};
            const mu = {mu};
            const starColor = "{star_color}";
            
            const showEarthOrbit = {str(show_earth_orbit).lower()};
            const showHabitableZone = {str(show_habitable_zone).lower()};
            const highlightPlanet = {str(highlight_planet).lower()};
            
            const hzInner = {hz_inner};
            const hzOuter = {hz_outer};

            const starRadAU = {star_rad} * SOLAR_RAD_TO_AU;
            const plRade = {pl_rade};
            const planetRadAU = plRade * EARTH_RAD_TO_AU;
            
            // 지구 데이터 (비교선용)
            const earthA = 1.0;
            const earthB = Math.sqrt(1 - Math.pow(0.0167, 2));
            const earthC = 0.0167;
            
            const paddingLeft = 70;
            const paddingRight = 40;
            const paddingTop = 40;
            const paddingBottom = 40;
            
            const plotWidth = canvas.width - (paddingLeft + paddingRight);
            const plotHeight = canvas.height - (paddingTop + paddingBottom);
            
            const baseLimitAU = (a + c) * 1.3; 
            
            let currentDays = 0;
            let isPlaying = true;
            let speedMultiplier = 1.0;
            let currentZoom = 1.0;
            
            controlBtn.addEventListener('click', () => {{
                isPlaying = !isPlaying;
                controlBtn.textContent = isPlaying ? "⏸ Pause" : "▶ Play";
                if (isPlaying) draw();
            }});
            
            function updateSpeed(btn, mult) {{
                [btn05, btn10, btn20].forEach(b => b.classList.remove('activeSpeed'));
                btn.classList.add('activeSpeed');
                speedMultiplier = mult;
            }}
            btn05.addEventListener('click', () => updateSpeed(btn05, 0.5));
            btn10.addEventListener('click', () => updateSpeed(btn10, 1.0));
            btn20.addEventListener('click', () => updateSpeed(btn20, 2.0));
            
            zoomSlider.addEventListener('input', (event) => {{
                let power = parseFloat(event.target.value);
                currentZoom = Math.pow(10, power);
                let displayTxt = currentZoom >= 1000 ? 
                                 (currentZoom/1000).toFixed(1) + "k x" : 
                                 currentZoom.toFixed(1) + "x";
                zoomVal.textContent = displayTxt;
            }});

            function draw() {{
                if (!isPlaying) return;

                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                let baseScale = Math.min(plotWidth, plotHeight) / (2 * baseLimitAU);
                let scale = baseScale * currentZoom;
                
                let screenCenterX = paddingLeft + (plotWidth / 2);
                let screenCenterY = paddingTop + (plotHeight / 2);
                
                let M_val = (2 * Math.PI / T) * currentDays;
                let E_val = M_val + e * Math.sin(M_val) + (e*e/2) * Math.sin(2*M_val);
                
                // 🛠️ [부호 교정] 타원 궤도의 기준점 위치 방향을 정상화 (-c 처리)
                let planetX_AU = a * Math.cos(E_val) - c;
                let planetY_AU = b * Math.sin(E_val);
                
                let focusX_AU = 0;
                let focusY_AU = 0;
                if (followPlanetCb.checked) {{
                    focusX_AU = planetX_AU;
                    focusY_AU = planetY_AU;
                }}
                
                function toCanvasX(xAU) {{ return screenCenterX + (xAU - focusX_AU) * scale; }}
                function toCanvasY(yAU) {{ return screenCenterY - (yAU - focusY_AU) * scale; }}
                
                // 그리드 렌더링
                ctx.lineWidth = 1;
                ctx.font = "11px 'Segoe UI'";
                
                let viewLimitAU = baseLimitAU / currentZoom;
                let logStep = Math.floor(Math.log10(viewLimitAU));
                let stepAU = Math.pow(10, logStep);
                if (viewLimitAU / stepAU < 2) stepAU /= 5;
                else if (viewLimitAU / stepAU < 5) stepAU /= 2;
                
                let startX_AU = Math.floor((focusX_AU - viewLimitAU*1.5) / stepAU) * stepAU;
                let endX_AU = focusX_AU + viewLimitAU*1.5;
                let startY_AU = Math.floor((focusY_AU - viewLimitAU*1.5) / stepAU) * stepAU;
                let endY_AU = focusY_AU + viewLimitAU*1.5;

                for (let xAU = startX_AU; xAU <= endX_AU; xAU += stepAU) {{
                    let cx = toCanvasX(xAU);
                    if (cx >= paddingLeft && cx <= paddingLeft + plotWidth) {{
                        ctx.strokeStyle = Math.abs(xAU) < stepAU*0.1 ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)';
                        ctx.beginPath(); ctx.moveTo(cx, paddingTop); ctx.lineTo(cx, paddingTop + plotHeight); ctx.stroke();
                        ctx.fillStyle = '#888';
                        let decimals = stepAU < 1 ? Math.max(0, -Math.floor(Math.log10(stepAU))) : 0;
                        ctx.fillText(xAU.toFixed(decimals) + " AU", cx + 2, paddingTop + plotHeight + 12);
                    }}
                }}
                
                for (let yAU = startY_AU; yAU <= endY_AU; yAU += stepAU) {{
                    let cy = toCanvasY(yAU);
                    if (cy >= paddingTop && cy <= paddingTop + plotHeight) {{
                        ctx.strokeStyle = Math.abs(yAU) < stepAU*0.1 ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)';
                        ctx.beginPath(); ctx.moveTo(paddingLeft, cy); ctx.lineTo(paddingLeft + plotWidth, cy); ctx.stroke();
                        ctx.fillStyle = '#888';
                        let decimals = stepAU < 1 ? Math.max(0, -Math.floor(Math.log10(stepAU))) : 0;
                        ctx.fillText(yAU.toFixed(decimals) + " AU", paddingLeft - 45, cy + 4);
                    }}
                }}
                
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
                ctx.strokeRect(paddingLeft, paddingTop, plotWidth, plotHeight);

                // 골디락스 존(생명체 거주가능 영역) 렌더링
                if (showHabitableZone) {{
                    ctx.save();
                    ctx.translate(toCanvasX(0), toCanvasY(0));
                    ctx.fillStyle = 'rgba(29, 209, 161, 0.08)';
                    ctx.beginPath();
                    ctx.arc(0, 0, hzOuter * scale, 0, 2 * Math.PI, false);
                    ctx.arc(0, 0, hzInner * scale, 0, 2 * Math.PI, true);
                    ctx.fill();
                    ctx.strokeStyle = 'rgba(29, 209, 161, 0.25)';
                    ctx.beginPath(); ctx.arc(0, 0, hzOuter * scale, 0, 2 * Math.PI); ctx.stroke();
                    ctx.beginPath(); ctx.arc(0, 0, hzInner * scale, 0, 2 * Math.PI); ctx.stroke();
                    ctx.restore();
                }}

                // 지구 궤도 비교선 렌더링 (항성은 0,0에 위치하므로 -earthC 적용)
                if (showEarthOrbit) {{
                    ctx.save();
                    ctx.translate(toCanvasX(-earthC), toCanvasY(0));
                    ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
                    ctx.lineWidth = 1.0;
                    ctx.setLineDash([2, 4]);
                    ctx.beginPath();
                    ctx.ellipse(0, 0, earthA * scale, earthB * scale, 0, 0, 2 * Math.PI);
                    ctx.stroke();
                    ctx.restore();
                }}

                // 대상 행성 궤도선 그리기 (항성은 0,0에 위치하므로 -c 적용)
                ctx.save();
                ctx.translate(toCanvasX(-c), toCanvasY(0));
                ctx.strokeStyle = 'rgba(74, 144, 226, 0.6)';
                ctx.lineWidth = 1.2;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.ellipse(0, 0, a * scale, b * scale, 0, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.restore();
                
                // 중심 항성 렌더링
                let renderStarRad = Math.max(0.5, starRadAU * scale); 
                ctx.beginPath();
                ctx.arc(toCanvasX(0), toCanvasY(0), renderStarRad, 0, 2 * Math.PI);
                ctx.fillStyle = starColor;
                ctx.shadowColor = starColor;
                ctx.shadowBlur = renderStarRad > 2 ? renderStarRad : 0;
                ctx.fill();
                ctx.shadowBlur = 0;
                
                // 행성 좌표 및 렌더링
                let pX = toCanvasX(planetX_AU);
                let pY = toCanvasY(planetY_AU);
                let renderPlanetRad = Math.max(0.5, planetRadAU * scale); 
                
                // 정밀 십자 지시선 렌더링
                if (highlightPlanet) {{
                    ctx.save();
                    ctx.strokeStyle = 'rgba(29, 209, 161, 0.8)'; 
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(pX - 16, pY); ctx.lineTo(pX - 5, pY);
                    ctx.moveTo(pX + 5, pY); ctx.lineTo(pX + 16, pY);
                    ctx.moveTo(pX, pY - 16); ctx.lineTo(pX, pY - 5);
                    ctx.moveTo(pX, pY + 5); ctx.lineTo(pX, pY + 16);
                    ctx.stroke();
                    ctx.restore();
                }}
                
                // 실제 크기의 행성 점 렌더링
                ctx.beginPath();
                ctx.arc(pX, pY, renderPlanetRad, 0, 2 * Math.PI);
                ctx.fillStyle = '#1dd1a1';
                ctx.fill();
                
                // 속도 계산
                let r_p = Math.sqrt(planetX_AU*planetX_AU + planetY_AU*planetY_AU);
                let v_kms = 0;
                if (r_p > 0 && (2/r_p - 1/a) > 0) {{
                    v_kms = Math.sqrt(mu * (2/r_p - 1/a)) * 149597870.7 / 86400;
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
    pl_rade_display = "정보 없음" if is_pl_rade_missing else f"{pl_rade:.3f} Earth Rad"
    
    info_text = (
        f"### 🪐 행성 특성 정보\n"
        f"* **이름:** `{p_data['pl_name']}`\n"
        f"* **행성 반지름:** `{pl_rade_display}` \n"
        f"* **공전 주기:** `{T:.1f} 일` \n"
        f"* **궤도 장반경:** `{a:.3f} AU` \n"
        f"* **궤도 이심률:** `{e:.3f}` \n\n"
        f"### ☀️ 중심 항성(별) 정보\n"
        f"* **항성 반지름:** `{star_rad_display}` \n"
        f"* **항성 질량:** `{check_val(p_data['st_mass'] if 'st_mass' in p_data else np.nan, 'Solar Mass')}`\n"
        f"* **항성 표면온도:** `{star_teff_display}`\n"
        f"* **분광형:** ` {star_spectral_type} `"
    )
    st.markdown(info_text)
