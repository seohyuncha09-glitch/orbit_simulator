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
st.markdown("NASA 아카이브 데이터를 기반으로 제작되었습니다. 상단 레이블과 재생/멈춤 제어가 포함된 최종 웹 가속 버전입니다.")

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
    
    # 💡 브라우저 내장 자바스크립트로 그리는 자막 + 재생 제어 컴포넌트 HTML
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ background-color: #111111; margin: 0; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white; }}
            #container {{ position: relative; width: 700px; height: 580px; margin: 0 auto; }}
            canvas {{ background: #111111; display: block; }}
            /* UI 텍스트 오버레이 디자인 */
            #infoOverlay {{ position: absolute; top: 15px; left: 20px; font-size: 15px; font-weight: bold; line-height: 1.5; pointer-events: none; }}
            #speedText {{ color: #1dd1a1; }}
            /* 제어 버튼 디자인 */
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
            
            // 파이썬 상수를 자바스크립트로 바인딩
            const a = {a};
            const e = {e};
            const b = {b};
            const c = {c};
            const T = {T};
            const mu = {mu};
            const starColor = "{star_color}";
            
            // 자동 축 고정 계산 스케일
            const limit = a * (1 + e) * 1.3;
            const scale = (canvas.width / 2) / limit;
            
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2 + 20; // 텍스트 공간 확보를 위해 살짝 아래로 중심 이동
            
            let currentDays = 0; // 경과 일수 계산 트리거
            let isPlaying = true; // 재생 제어 플래그
            
            // 재생 / 일시정지 토글 함수
            controlBtn.addEventListener('click', () => {{
                isPlaying = !isPlaying;
                controlBtn.textContent = isPlaying ? "⏸ Pause" : "▶ Play";
                if (isPlaying) draw(); // 다시 재생 시 애니메이션 루프 재가동
            }});

            function draw() {{
                if (!isPlaying) return; // 일시정지 상태면 그리기 중단

                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // 1. 모눈망 배경
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
                ctx.lineWidth = 1;
                for(let i=0; i<canvas.width; i+=50) {{
                    ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke();
                    ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke();
                }}
                
                // 2. 푸른색 공전 궤도선
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
                ctx.arc(centerX, centerY, Math.max(8, Math.min({star_rad} * 12, 35)), 0, 2 * Math.PI);
                ctx.fillStyle = starColor;
                ctx.shadowColor = starColor;
                ctx.shadowBlur = 15;
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 1;
                ctx.stroke();
                
                // 4. 경과 시간을 이용한 평균 근점 이각(M) 구하기 및 케플러 방정식 풀이
                let M_val = (2 * Math.PI / T) * currentDays;
                let E = M_val + e * Math.sin(M_val) + (e*e/2) * Math.sin(2*M_val); // 근사식 이용
                
                let planetX = centerX - (c * scale) + (a * scale * Math.cos(E));
                let planetY = centerY + (b * scale * Math.sin(E));
                
                // 5. 초록색 외계행성
                ctx.beginPath();
                ctx.arc(planetX, planetY, 7, 0, 2 * Math.PI);
                ctx.fillStyle = '#1dd1a1';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();
                
                // 6. 실시간 궤도 속도 물리 연산 및 레이블 글씨 갱신
                let r_p = Math.sqrt(Math.pow((planetX - centerX)/scale + c, 2) + Math.pow((planetY - centerY)/scale, 2));
                let v_kms = 0;
                if (r_p > 0 && (2/r_p - 1/a) > 0) {{
                    let v_au = Math.sqrt(mu * (2/r_p - 1/a));
                    v_kms = v_au * 149597870.7 / 86400;
                }}
                
                timeLabel.innerHTML = `<b>Time: ${{currentDays.toFixed(1)}} / ${{T.toFixed(1)}} days</b>`;
                speedLabel.innerHTML = `<b>Speed: ${{v_kms.toFixed(2)}} km/s</b>`;
                
                // 7. 시간 간격 증가 및 무한 루프 처리
                let dt = T / 250; // 속도가 너무 빠르면 분모 숫자를 키우세요
                currentDays += dt;
                if (currentDays >= T) currentDays = 0; // 한 바퀴 끝나면 0초로 자동 리셋
                
                requestAnimationFrame(draw);
            }}
            
            // 즉시 구동
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
