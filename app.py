with col1:
    st.subheader(f"✨ {selected_planet} 궤도 실시간 플롯")
    
    fig = go.Figure()
    
    # 1. 궤도선 추가
    fig.add_trace(go.Scatter(x=x_orbit, y=y_orbit, mode='lines', line=dict(color='#4A90E2', width=1.5, dash='dash'), name='Orbit'))
    # 2. 중심 항성 추가
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', marker=dict(color=star_color, size=star_size, line=dict(color='white', width=0.5)), name='Star'))
    # 3. 현재 시점의 행성 위치 추가
    fig.add_trace(go.Scatter(x=[x_curr], y=[y_curr], mode='markers', marker=dict(color='#1dd1a1', size=10), name='Planet'))
    
    # 💡 [해결책] 대입(=) 대신 update_layout 및 전용 메서드로 안전하게 속성 변경
    fig.update_layout(
        title=dict(text=f"<b>🪐 {selected_planet} (Day: {current_day:.1f} / {T:.1f}) | Speed: {v_kms:.2f} km/s</b>", font=dict(color='white', size=15)),
        template="plotly_dark",
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        width=650,
        height=650,
        showlegend=False
    )
    
    # 💡 에러가 나던 xaxis, yaxis 설정을 가장 안전한 전용 메서드로 분리 주입
    fig.update_xaxes(title_text="X Distance (AU)", gridcolor="rgba(128,128,128,0.15)", showzeroline=False)
    fig.update_yaxes(title_text="Y Distance (AU)", gridcolor="rgba(128,128,128,0.15)", showzeroline=False)
    
    st.plotly_chart(fig, use_container_width=True)
