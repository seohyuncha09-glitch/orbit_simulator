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
    st.error("CSV 파일을 찾을 수 없습니다. 'PS_data.csv' 파일이 저장소에 있는지 확인해 주세요.")
    st.stop()

# ==========================================
# 2. 웹 UI 구성
# ==========================================
st.set_page_config(page_title="공전 궤도 시뮬레이터", layout="wide")

st.title("공전 궤도 시뮬레이터")
st.markdown("NASA Exoplanet Archive를 기반으로 한 궤도 시뮬레티터입니다.")

# ⚙️ 사이드바 제어 패널
st.sidebar.header("⚙️ 제어 패널")
selected_planet = st.sidebar.selectbox("🪐 탐색할 행성 선택", all_planet_names, key="sidebar_planet_selector")

st.sidebar.markdown("---")
show_earth_orbit = st.sidebar.checkbox("🌍 지구 궤도 비교선 표시", value=False)
show_habitable_zone = st.sidebar.checkbox("🟢 골디락스 존 표시", value=False)
real_star_scale = st.sidebar.checkbox("🪐 실제 항성 비율로 보기", value=False)

# 행성 데이터 추출
p_data = df[df['pl_name'] == selected_planet].iloc[0]
a = float(p_data['pl_orbsmax'])
e = float(p_data['pl_orbeccen']) if not pd.isna(p_data['pl_orbeccen']) else 0.0
T = float(p_data['pl_orbper'])

b = a * np.sqrt(1 - e**2)
c = a * e
mu = (4 * np.pi**2 * (a**3)) / (T**2) if T > 0 else 1.0

# 항성 정보
is_star_rad_missing = 'st_rad' not in p_data or pd.isna(p_data['st_rad'])
star_rad = 1.0 if is_star_rad_missing else float(p_data['st_rad'])
star_teff = p_data['st_teff'] if 'st_teff' in p_data else np.nan
star_mass = float(p_data['st_mass']) if 'st_mass' in p_data and not pd.isna(p_data['st_mass']) else 1.0

# ==========================================
# [수정] 항성의 실제 광도를 반영한 골디락스 존 계산
# ==========================================
# 1. 광도(L) 구하기 (태양 광도 기준 배율)
if 'st_lum' in p_data and not pd.isna(p_data['st_lum']):
    # 아카이브에 광도 데이터가 직접 존재하는 경우 (log10 형태가 아닐 때)
    star_lum = 10**float(p_data['st_lum']) if 'log' in str(df['st_lum'].dtype) else float(p_data['st_lum'])
elif not pd.isna(star_rad) and not pd.isna(star_teff):
    # 반지름과 표면온도로 광도 유도 (L = R^2 * (T/T_sun)^4)
    # 태양 표면온도 = 5778 K
    star_lum = (star_rad**2) * ((star_teff / 5778)**4)
else:
    # 데이터가 아예 없으면 항성 질량을 이용해 약식 추정 (주계열성 L ~ M^3.5)
    star_lum = star_mass**3.5

# 2. 광도의 제곱근을 기반으로 정밀한 골디락스 존(HZ) 범위 계산
hz_inner = 0.75 * np.sqrt(star_lum)
hz_outer = 1.77 * np.sqrt(star_lum)

def get_star_info(teff):
    if pd.isna(teff): return '#FF9F43', '정보 없음'
    if teff >= 10000: return '#9bb0ff', 'O/B형 (청색)'
    elif teff >= 7500: return '#aabfff', 'A형 (백색)'
    elif teff >= 6000: return '#f8f7ff', 'F형 (황백색)'
    elif teff >= 5200: return '#fff4ea', 'G형 (황색)'
    elif teff >= 3700: return '#ffd2a1', 'K형 (주황색)'
    else: return '#ff8585', 'M형 (적색)'

star_color, star_spectral_type = get_star_info(star_teff)

# ------------------------------------------
# 시각화 레이아웃
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
            body {{ background-color: #111111; margin: 0; font-family: sans-serif; color: white; overflow: hidden; }}
            #container {{ position: relative; width: 100%; max-width: 700px; margin: 0 auto; }}
            canvas {{ background: #111111; display: block; width: 100%; height: auto; }}
            #infoOverlay {{ position: absolute; top: 15px; left: 20px; font-size: 13px; font-weight: bold; pointer-events: none; }}
            #speedText {{ color: #1dd1a1; }}
            #mainControls {{ background: #1a1a1a; padding: 15px; border-radius: 8px; margin-top: 10px; display: flex; flex-direction: column; gap: 12px; border: 1px solid #333; }}
            .row {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: center; }}
            .uiBtn {{ background: #111111; border: 1px solid #555; color: white; padding: 6px 12px; font-size: 12px; border-radius: 4px; cursor: pointer; }}
            .activeSpeed {{ background: #1dd1a1 !important; color: #111 !important; border-color: #1dd1a1 !important; }}
            .sliderContainer {{ display: flex; align-items: center; gap: 10px; font-size: 13px; flex-grow: 1; }}
            .sliderContainer input {{ flex-grow: 1; accent-color: #1dd1a1; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="infoOverlay">
                <div id="timeText">Time: 0.0 days</div>
                <div id="speedText">Speed: 0.00 km/s</div>
            </div>
            <canvas id="orbitCanvas" width="700" height="520"></canvas>
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
                    <input type="range" id="zoomSlider" min="0.1" max="5.0" step="0.1" value="1.0">
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
            const zoomSlider = document.getElementById('zoomSlider');
            const zoomVal = document.getElementById('zoomVal');
            
            const a = {a}, e = {e}, b = {b}, c = {c}, T = {T}, mu = {mu}, starColor = "{star_color}";
            const showEarthOrbit = {str(show_earth_orbit).lower()}, showHabitableZone = {str(show_habitable_zone).lower()}, realStarScale = {str(real_star_scale).lower()};
            const hzInner = {hz_inner}, hzOuter = {hz_outer};
            
            const earthA = 1.0, earthE = 0.0167;
            const earthB = earthA * Math.sqrt(1 - Math.pow(earthE, 2));
            const earthC = earthA * earthE;
            
            const paddingLeft = 70, plotWidth = canvas.width - 110, plotHeight = canvas.height - 80;
            const baseLimit = (a + c) * 1.3;
            
            let currentDays = 0, isPlaying = true, speedMultiplier = 1.0, currentZoom = 1.0;

            controlBtn.onclick = () => {{ isPlaying = !isPlaying; controlBtn.textContent = isPlaying ? "⏸ Pause" : "▶ Play"; if (isPlaying) draw(); }};
            zoomSlider.oninput = (ev) => {{ currentZoom = parseFloat(ev.target.value); zoomVal.textContent = currentZoom.toFixed(1) + "x"; }};

            // 배속 버튼 처리
            const sBtns = [document.getElementById('speed05'), document.getElementById('speed10'), document.getElementById('speed20')];
            const sVals = [0.5, 1.0, 2.0];
            sBtns.forEach((btn, idx) => {{
                btn.onclick = () => {{
                    sBtns.forEach(b => b.classList.remove('activeSpeed'));
                    btn.classList.add('activeSpeed');
                    speedMultiplier = sVals[idx];
                }};
            }});

            function draw() {{
                if (!isPlaying) return;
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                let limit = baseLimit / currentZoom;
                let scale = Math.min(plotWidth, plotHeight) / (2 * limit);
                let centerX = paddingLeft + (plotWidth / 2) - (plotWidth * 0.1);
                let centerY = canvas.height / 2;

                // 그리드 및 눈금 (생략 가능하나 유지)
                ctx.lineWidth = 1; ctx.font = "10px sans-serif"; ctx.fillStyle = "#888";
                let step = limit > 5 ? 2 : (limit < 0.5 ? 0.1 : 1);
                for(let i = -Math.floor(limit*2); i <= limit*2; i+=step) {{
                    let x = centerX + i * scale;
                    if(x > paddingLeft && x < paddingLeft+plotWidth) {{
                        ctx.strokeStyle = "rgba(255,255,255,0.05)";
                        ctx.beginPath(); ctx.moveTo(x, 40); ctx.lineTo(x, canvas.height-40); ctx.stroke();
                        ctx.fillText(i.toFixed(1)+"AU", x-10, canvas.height-25);
                    }}
                }}

                // 골디락스 존
                if (showHabitableZone) {{
                    ctx.save(); ctx.translate(centerX, centerY);
                    ctx.fillStyle = 'rgba(29, 209, 161, 0.1)'; ctx.strokeStyle = 'rgba(29, 209, 161, 0.3)';
                    ctx.beginPath(); ctx.arc(0, 0, hzOuter * scale, 0, Math.PI*2); ctx.arc(0, 0, hzInner * scale, 0, Math.PI*2, true); ctx.fill(); ctx.stroke();
                    ctx.restore();
                }}

                // 지구 궤도
                if (showEarthOrbit) {{
                    ctx.save(); ctx.translate(centerX + (earthC * scale), centerY);
                    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)'; ctx.setLineDash([2, 4]);
                    ctx.beginPath(); ctx.ellipse(0, 0, earthA * scale, earthB * scale, 0, 0, Math.PI*2); ctx.stroke();
                    ctx.restore();
                }}

                // 행성 궤도
                ctx.save(); ctx.translate(centerX + (c * scale), centerY);
                ctx.strokeStyle = '#4A90E2'; ctx.lineWidth = 1.5; ctx.setLineDash([5, 5]);
                ctx.beginPath(); ctx.ellipse(0, 0, a * scale, b * scale, 0, 0, Math.PI*2); ctx.stroke();
                ctx.restore();
                
                // ⚙️ 항성 그리기 (확대 로직 수정)
                ctx.beginPath();
                let finalStarRad;
                
                if (realStarScale) {{
                    // 실제 비율 모드: 1 Solar Rad ≈ 0.00465 AU 임을 적용하여 scale에 비례하게 함
                    let trueRadInAU = {star_rad} * 0.00465;
                    finalStarRad = trueRadInAU * scale; 
                    // 줌을 당겨도 너무 작아서 안 보일 수 있으므로 최소 1.5px 보정
                    if (finalStarRad < 1.5) finalStarRad = 1.5;
                }} else {{
                    // 가독성 모드: scale에 정비례하여 커지도록 설정 (줌 제한 해제)
                    // scale 자체가 currentZoom에 비례하므로 scale을 기준으로 잡음
                    let readableFactor = ({star_rad} * 15); // 기본 크기 결정 인자
                    finalStarRad = (readableFactor * scale) / (baseLimit * 0.5); 
                    
                    // 너무 커져서 화면을 다 덮는 것만 방지 (최대 180px)
                    if (finalStarRad > 180) finalStarRad = 180;
                    // 최소 크기 보장
                    if (finalStarRad < 5) finalStarRad = 5;
                }}
                
                ctx.arc(centerX, centerY, finalStarRad, 0, Math.PI * 2);
                ctx.fillStyle = starColor;
                ctx.shadowColor = starColor;
                ctx.shadowBlur = realStarScale ? 3 : (10 * currentZoom / 2); // 빛번짐도 줌에 비례
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // 행성 위치
                let M = (2 * Math.PI / T) * currentDays;
                let E = M + e * Math.sin(M);
                let px = centerX + (c * scale) + (a * scale * Math.cos(E));
                let py = centerY + (b * scale * Math.sin(E));
                
                ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI*2);
                ctx.fillStyle = '#1dd1a1'; ctx.fill(); ctx.strokeStyle = '#fff'; ctx.stroke();
                
                // 속도 계산 및 표시
                let r_dist = Math.sqrt(Math.pow((px-centerX)/scale, 2) + Math.pow((py-centerY)/scale, 2));
                let v = Math.sqrt(mu * (2/r_dist - 1/a)) * 149597870.7 / 86400;
                timeLabel.textContent = "Time: " + currentDays.toFixed(1) + " days";
                speedLabel.textContent = "Speed: " + v.toFixed(2) + " km/s";
                
                currentDays += (T / 400) * speedMultiplier;
                if (currentDays >= T) currentDays = 0;
                requestAnimationFrame(draw);
            }}
            draw();
        </script>
    </body>
    </html>
    """
    st.components.v1.html(html_code, height=680)

with col2:
    st.subheader("📊 데이터")
    def check_val(val, unit=""): return f"{val:.3f} {unit}" if not pd.isna(val) else "정보 없음"
    star_rad_display = "정보 없음" if is_star_rad_missing else f"{star_rad:.3f} Solar Rad"
    
    st.markdown(f"""
    ### 🪐 행성 특성
    * **이름:** `{p_data['pl_name']}`
    * **공전 주기:** `{T:.1f} 일`
    * **궤도 장반경:** `{a:.3f} AU`
    * **궤도 이심률:** `{e:.3f}`
    
    ### ☀️ 중심 항성
    * **항성 반지름:** `{star_rad_display}`
    * **항성 질량:** `{check_val(p_data['st_mass'] if 'st_mass' in p_data else np.nan, 'Solar Mass')}`
    * **표면 온도:** `{f"{star_teff:.0f} K" if not pd.isna(star_teff) else "정보 없음"}`
    * **분광형:** `{star_spectral_type}`
    """)
