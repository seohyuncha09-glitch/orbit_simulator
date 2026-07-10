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
st.markdown("NASA 아카이브 데이터를 기반으로 제작되었습니다. 궤도 크기에 따라 축 범위가 자동으로 확장되며 숫자 눈금이 표시됩니다.")

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
    
    # 💡 자바스크립트 내부에 가변 축 스케일링 및 숫자 눈금 그리기 로직 추가
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ background-color: #111111; margin: 0; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white; }}
            #container {{ position: relative; width: 700px; height: 580px; margin: 0 auto; }}
            canvas {{ background: #111111; display: block; }}
            #infoOverlay {{ position: absolute; top: 15px; left: 20px; font-size: 15px; font-weight: bold; line-height: 1.5; pointer-events: none; }}
            #speedText {{ color: #1dd1a1; }}
            #controlBtn {{ 
                position: absolute; bottom: 15px; left: 20px; 
                background: #111111; border: 1px solid #555555; color: white; 
                padding: 6px 12px; font-size: 13px; font-weight: bold; border-radius: 4px; cursor: pointer; 
                transition: all 0.2s;
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
            
            // 💡 [가변 범위 핵심] 행성 궤도의 최대 반경(원점 기준 원일점 거리)을 계산해 여유 있게 여백(1.4배)을 둡니다.
            const maxOrbitRadius = a * (1 + e);
            const limit = maxOrbitRadius * 1.4;
            
            // 패딩(여백)을 고려해 그리기 영역 제한 (눈금 표시용 공간 좌측/하단 40px 확보)
            const plotWidth = canvas.width - 60;
            const plotHeight = canvas.height - 60;
            const startX = 50;
            const startY = 20;
            
            // 1 AU가 화면에서 차지할 픽셀 가동 스케일
            const scale = (plotWidth / 2) / limit;
            
            // 천체 시스템의 정중앙 좌표 (이전과 달리 축 눈금 공간 때문에 약간 시프트)
            const centerX = startX + (plotWidth / 2);
            const centerY = startY + (plotHeight / 2);
            
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
                
                // 💡 1. 축 가이드 라인 및 숫자 눈금 그리기
                ctx.lineWidth = 1;
                ctx.font = "11px 'Segoe UI'";
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                
                // 적절한 눈금 간격(AU 단위) 자동 설정
                let stepAU = 1;
                if (limit > 5) stepAU = 2;
                if (limit > 15) stepAU = 5;
                if (limit > 50) stepAU = 20;
                if (limit > 200) stepAU = 50;
                if (limit < 0.5) stepAU = 0.1;

                // X축 눈금선 및 모눈망 격자
                for (let xAU = -Math.floor(limit); xAU <= limit; xAU += stepAU) {{
                    if (xAU === 0) continue;
                    let canvasX = centerX + (xAU * scale);
                    if (canvasX >= startX && canvasX <= startX + plotWidth) {{
                        // 세로 격자 그리드
                        ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
                        ctx.beginPath(); ctx.moveTo(canvasX, startY); ctx.lineTo(canvasX, startY + plotHeight); ctx.stroke();
                        
                        // 하단 X축 숫자 눈금 표시
                        ctx.fillStyle = '#888888';
                        ctx.fillText(xAU.toFixed(limit < 1 ? 1 : 0), canvasX, startY + plotHeight + 5);
                        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
                        ctx.beginPath(); ctx.moveTo(canvasX, startY + plotHeight); ctx.lineTo(canvasX, startY + plotHeight + 4); ctx.stroke();
                    }}
                }}
                
                // Y축 눈금선 및 모눈망 격자
                ctx.textAlign = "right";
                ctx.textBaseline = "middle";
                for (let yAU = -Math.floor(limit); yAU <= limit; yAU += stepAU) {{
                    if (yAU === 0) continue;
                    let canvasY = centerY - (yAU * scale); // 캔버스는 상단이 (-)이므로 보정
                    if (canvasY >= startY && canvasY <= startY + plotHeight) {{
                        // 가로 격자 그리드
                        ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
                        ctx.beginPath(); ctx.moveTo(startX, canvasY); ctx.lineTo(startX + plotWidth, canvasY); ctx.stroke();
                        
                        // 좌측 Y축 숫자 눈금 표시
                        ctx.fillStyle = '#888888';
                        ctx.fillText(yAU.toFixed(limit < 1 ? 1 : 0), startX - 8, canvasY);
                        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
                        ctx.beginPath(); ctx.moveTo(startX, canvasY); ctx.lineTo(startX - 4, canvasY); ctx.stroke();
                    }}
                }}

                // 메인 바깥 외곽 축선 그리기 (Border)
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
                ctx.strokeRect(startX, startY, plotWidth, plotHeight);

                // 2. 푸른색 공전 궤도선 (축 락이 걸린 상태에서 타원 이동)
                ctx.save();
                ctx.translate(centerX - (c * scale), centerY);
                ctx.strokeStyle = '#4A90E2';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([5, 5]);
                ctx.beginPath();
                ctx.ellipse(0, 0, a * scale, b * scale, 0, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.restore();
                
                // 3. 중심 항성 (태양)
                ctx.beginPath();
                ctx.arc(centerX, centerY, Math.max(8, Math.min({star_rad} * 12, 32)), 0, 2 * Math.PI);
                ctx.fillStyle = starColor;
                ctx.shadowColor = starColor;
                ctx.shadowBlur = 15;
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // 4. 행성 위치 연산
                let M_val = (2 * Math.PI / T) * currentDays;
                let E = M_val + e * Math.sin(M_val) + (e*e/2) * Math.sin(2*M_val);
                
                let planetX = centerX - (c * scale) + (a * scale * Math.cos(E));
                let planetY = centerY + (b * scale * Math.sin(E));
                
                // 5. 초록색 외계행성
                ctx.beginPath();
                ctx.arc(planetX, planetY, 7, 0, 2 * Math.PI);
                ctx.fillStyle = '#1dd1a1';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();
                
                // 6. 속도 계산 및 오버레이 컴포넌트 데이터 텍스트 출력
                let r_p = Math.sqrt(Math.pow((planetX - centerX)/scale + c, 2) + Math.pow((planetY - centerY)/scale, 2));
                let v_kms = 0;
                if (r_p > 0 && (2/r_p - 1/a) > 0) {{
                    let v_au = Math.sqrt(mu * (2/r_p - 1/a));
                    v_kms = v_au * 149597870.7 / 86400;
                }}
                
                timeLabel.innerHTML = `<b>Time: ${{currentDays.toFixed(1)}} / ${{T.toFixed(1)}} days</b>`;
                speedLabel.innerHTML = `<b>Speed: ${{v_kms.toFixed(2)}} km/s</b>`;
                
                // 7. 타임라인 증가 및 무한 루프 리셋
                let dt = T / 300; 
                currentDays += dt;
                if (currentDays >= T) currentDays = 0;
                
                requestAnimationFrame(draw);
            }}
            
            draw();
        </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=600)

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
