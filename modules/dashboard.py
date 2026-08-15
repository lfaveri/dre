import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import database as db
import tri_engine
from theme_pre_enem import render_brand_header

def render_dashboard_view():
    render_brand_header("Acompanhamento da Turma", "Simulador TRI · Painel Geral")
    st.markdown("<p style='color:var(--ink-soft); margin-top:-6px;'>Painel analítico psicométrico com notas TRI no padrão ENEM, curvas psicométricas dos itens e distribuição de respostas.</p>", unsafe_allow_html=True)

    quizzes = db.get_all_quizzes()
    if not quizzes:
        st.info("Nenhum questionário encontrado para exibir estatísticas.")
        return

    # Seletor de Quiz no topo com botão de atualização rápida
    col_sel, col_ref = st.columns([4, 1])
    with col_sel:
        quiz_map = {f"{q['title']} (Código: {q['quiz_code']}) — {q['submission_count']} respostas": q['id'] for q in quizzes}
        selected_label = st.selectbox("Selecione a Avaliação:", list(quiz_map.keys()))
        selected_quiz_id = quiz_map[selected_label]
    
    with col_ref:
        st.write("")
        st.write("")
        if st.button("Atualizar Dados", use_container_width=True, type="primary"):
            st.rerun()

    analytics = db.get_quiz_analytics_data(selected_quiz_id)
    quiz_info = analytics.get('quiz', {})
    submissions = analytics.get('submissions', [])
    questions_stat = analytics.get('questions_stat', [])
    options_breakdown = analytics.get('options_breakdown', [])

    if not submissions:
        st.warning(f"Nenhuma resposta registrada ainda para o questionário '{quiz_info.get('title')}'.")
        st.info("Peça aos alunos para escanearem o QR Code gerado na Área do Professor.")
        return

    df_subs = pd.DataFrame(submissions)

    # Garantir colunas TRI caso venham de submissões antigas
    if 'tri_score' not in df_subs.columns:
        df_subs['tri_score'] = 500.0
    if 'theta' not in df_subs.columns:
        df_subs['theta'] = 0.0
    if 'coherence_label' not in df_subs.columns:
        df_subs['coherence_label'] = 'Coerente'

    # =========================================================================
    # MÉTRICAS PRINCIPAIS (DESIGN DO PAINEL PRÉ-ENEM)
    # =========================================================================
    total_students = len(df_subs)
    avg_tri = df_subs['tri_score'].mean()
    max_tri = df_subs['tri_score'].max()
    avg_pct = df_subs['percentage'].mean()
    avg_acertos = df_subs['score'].mean()
    tot_pts = df_subs['total_points'].iloc[0] if not df_subs.empty and df_subs['total_points'].iloc[0] > 0 else 1

    st.markdown(f"""
    <div style="background: var(--panel-bg); border-radius: 18px; padding: 22px; margin: 16px 0 24px 0; color: #F3FBFB; border: 1px solid var(--panel-line);">
        <div style="display: flex; gap: 32px; flex-wrap: wrap;">
            <div>
                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--panel-sub); text-transform: uppercase; font-weight: 600;">Respondentes</span>
                <div style="font-family: var(--font-display); font-size: 32px; font-weight: 700; color: #ffffff;">{total_students}</div>
            </div>
            <div>
                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--panel-sub); text-transform: uppercase; font-weight: 600;">Nota Média Simulada</span>
                <div style="font-family: var(--font-display); font-size: 32px; font-weight: 700; color: var(--teal);">{avg_tri:.0f} <span style="font-size:16px; color:var(--panel-sub);">pts</span></div>
            </div>
            <div>
                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--panel-sub); text-transform: uppercase; font-weight: 600;">Média de Acertos</span>
                <div style="font-family: var(--font-display); font-size: 32px; font-weight: 700; color: var(--yellow);">{avg_acertos:.1f} / {tot_pts:.0f}</div>
            </div>
            <div>
                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--panel-sub); text-transform: uppercase; font-weight: 600;">Aproveitamento Médio</span>
                <div style="font-family: var(--font-display); font-size: 32px; font-weight: 700; color: #ffffff;">{avg_pct:.1f}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================================
    # GRÁFICOS DINÂMICOS COM PLOTLY
    # =========================================================================
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Dispersão: Aproveitamento (%) vs. Nota TRI (ENEM)")
        st.caption("Alunos com mesmo número de acertos têm notas diferentes conforme a coerência pedagógica.")
        
        color_map = {
            "Alta Coerência Pedagógica": "#2FC9D2",      # Teal
            "Coerência Regular": "#FDDE40",              # Yellow
            "Indício de Chute (Incoerente)": "#F2564F",  # Coral
            "Coerente": "#1FA8B0"
        }

        fig_disp = px.scatter(
            df_subs,
            x="percentage",
            y="tri_score",
            color="coherence_label",
            color_discrete_map=color_map,
            hover_data=["student_name", "score", "theta"],
            labels={"percentage": "Aproveitamento Clássico (%)", "tri_score": "Nota TRI (Escala ENEM)", "coherence_label": "Coerência"},
            title="Efeito da Coerência Pedagógica na Nota TRI"
        )
        fig_disp.update_traces(marker=dict(size=13, opacity=0.9, line=dict(width=1.5, color='#073036')))
        fig_disp.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(234, 250, 250, 0.5)",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_disp, use_container_width=True)

    with col_chart2:
        st.subheader("Distribuição das Notas Simuladas")
        st.caption("Histograma das notas estimadas na régua do ENEM (Média 500 / Desvio 100).")
        fig_hist = px.histogram(
            df_subs,
            x="tri_score",
            nbins=10,
            color_discrete_sequence=["#2FC9D2"],
            labels={"tri_score": "Nota TRI (ENEM)", "count": "Qtd. Alunos"},
            title="Distribuição das Notas TRI na Turma"
        )
        fig_hist.update_layout(
            bargap=0.1,
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(234, 250, 250, 0.5)",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # =========================================================================
    # CURVAS CARACTERÍSTICAS DOS ITENS (CCI - MODELO 3PL DO ENEM)
    # =========================================================================
    if questions_stat:
        with st.expander("📈 Curvas Características dos Itens (CCI - Modelo Logístico 3PL)", expanded=True):
            st.markdown("""
            A **Curva Característica do Item (CCI)** mostra a probabilidade esperada de um aluno acertar a questão conforme seu nível de conhecimento (proficiência $\\theta$):
            - **Questões Fáceis:** Curva deslocada para a esquerda (alta chance de acerto mesmo com proficiência menor).
            - **Questões Difíceis:** Curva deslocada para a direita (exige maior proficiência para acertar).
            - **Assíntota Inferior ($c$):** Probabilidade de acerto ao acaso (chute).
            """)
            
            fig_cci = go.Figure()
            
            # Paleta de cores oficial do Pré-Enem Digital MT
            colors = ["#2FC9D2", "#FDDE40", "#F2564F", "#1FA8B0", "#E8C520", "#DC3E3A"]
            
            for idx, q_item in enumerate(questions_stat):
                a_val = q_item.get('param_a') if q_item.get('param_a') is not None else 1.2
                b_val = q_item.get('param_b') if q_item.get('param_b') is not None else 0.0
                c_val = q_item.get('param_c') if q_item.get('param_c') is not None else 0.25
                d_level = q_item.get('difficulty_level', 'Média')
                
                pts = tri_engine.get_icc_curve_points(a_val, b_val, c_val)
                color = colors[idx % len(colors)]
                
                fig_cci.add_trace(go.Scatter(
                    x=pts['enem_scale'],
                    y=pts['probability'],
                    mode='lines',
                    name=f"Q{q_item['order_num']} ({d_level}) [b={b_val}]",
                    line=dict(width=3, color=color),
                    hovertemplate=f"<b>Q{q_item['order_num']}</b><br>Nota ENEM: %{{x:.0f}}<br>P(Acerto): %{{y:.2%}}<extra></extra>"
                ))
            
            fig_cci.update_layout(
                title="Curvas Características dos Itens (CCI - Escala ENEM)",
                xaxis_title="Proficiência (Régua ENEM de 300 a 900)",
                yaxis_title="Probabilidade de Acerto P(θ)",
                yaxis=dict(range=[0, 1.05], tickformat=".0%"),
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(234, 250, 250, 0.5)",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=60, b=20)
            )
            st.plotly_chart(fig_cci, use_container_width=True)

    # =========================================================================
    # TAXA DE ACERTO E DISTRATORES POR QUESTÃO
    # =========================================================================
    if questions_stat:
        with st.expander("🔍 Análise Pedagógica: Taxa de Acertos e Distratores", expanded=False):
            col_b1, col_b2 = st.columns([1, 1])
            with col_b1:
                df_q = pd.DataFrame(questions_stat)
                df_q['label'] = [f"Q{q['order_num']} ({q.get('difficulty_level', 'M')})" for q in questions_stat]
                
                bar_colors = []
                for rate in df_q['success_rate']:
                    if rate >= 70:
                        bar_colors.append("#2FC9D2")
                    elif rate >= 40:
                        bar_colors.append("#FDDE40")
                    else:
                        bar_colors.append("#F2564F")

                fig_bar = px.bar(
                    df_q,
                    x="label",
                    y="success_rate",
                    text="success_rate",
                    hover_data=["question_text", "total_answers", "correct_answers"],
                    labels={"label": "Questão", "success_rate": "% Acertos"},
                    title="% de Acertos Reais por Questão"
                )
                fig_bar.update_traces(marker_color=bar_colors, texttemplate='%{text:.1f}%', textposition='outside')
                fig_bar.update_layout(
                    yaxis=dict(range=[0, 110]),
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(234, 250, 250, 0.5)",
                    height=320,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_b2:
                if options_breakdown:
                    st.markdown("**Alternativas mais marcadas:**")
                    df_opts = pd.DataFrame(options_breakdown)
                    for q_stat in questions_stat:
                        q_id = q_stat['question_id']
                        subset = df_opts[df_opts['question_id'] == q_id]
                        if not subset.empty:
                            st.caption(f"**Q{q_stat['order_num']}:** {q_stat['question_text'][:70]}...")
                            for _, opt in subset.iterrows():
                                tag = " (Gabarito)" if opt['is_correct'] else ""
                                st.write(f"- {opt['option_text']}{tag}: **{opt['pick_count']} escolha(s)**")
                            st.markdown("---")

    # =========================================================================
    # TABELA DE RANKING E CLASSIFICAÇÃO COM TRI
    # =========================================================================
    st.subheader("Ranking Geral da Turma (Classificação por Nota TRI)")
    
    # Preparar DataFrame com classificação
    df_display = df_subs.copy()
    
    ranking_col = [f"{i+1}º Lugar" for i in range(len(df_display))]
    df_display.insert(0, "Classificação", ranking_col)
    
    # Formatação de colunas para exibição limpa
    df_display['Código PIN'] = df_display['student_pin'].fillna("-")
    df_display['Nota TRI (ENEM)'] = df_display['tri_score'].apply(lambda x: f"{x:.1f}")
    df_display['Proficiência (θ)'] = df_display['theta'].apply(lambda x: f"{x:+.2f} DP")
    df_display['Aproveitamento'] = df_display['percentage'].apply(lambda x: f"{x:.1f}%")
    df_display['Pontos Clássicos'] = df_display.apply(lambda r: f"{r['score']:.1f} / {r['total_points']:.1f}", axis=1)

    df_display = df_display.rename(columns={
        "student_name": "Nome / Identificação",
        "coherence_label": "Coerência Pedagógica",
        "submitted_at": "Data/Hora"
    })
    
    cols_to_show = [
        "Classificação", "Código PIN", "Nome / Identificação", "Nota TRI (ENEM)",
        "Proficiência (θ)", "Coerência Pedagógica", "Pontos Clássicos", "Aproveitamento", "Data/Hora"
    ]
    
    st.dataframe(
        df_display[cols_to_show],
        use_container_width=True,
        hide_index=True
    )

    # Botão de Exportação CSV com todos os dados da TRI
    csv_data = df_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Baixar Relatório Psicométrico Completo em CSV (Excel)",
        data=csv_data,
        file_name=f"relatorio_tri_enem_{quiz_info.get('quiz_code', 'quiz')}.csv",
        mime="text/csv",
        use_container_width=True
    )

