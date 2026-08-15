import streamlit as st
import database as db
from theme_pre_enem import render_brand_header, LOGO_PRE_ENEM_BASE64

def get_difficulty_badge_html(difficulty_level: str) -> str:
    level = (difficulty_level or 'Média').lower().strip()
    if 'fácil' in level or 'facil' in level:
        return '<span class="tag-diff tag-facil"><svg viewBox="0 0 24 24" width="12" height="12"><path d="M7 5v14l12-7z" fill="#1FA8B0"/></svg> Fácil</span>'
    elif 'difícil' in level or 'dificil' in level:
        return '<span class="tag-diff tag-dificil"><svg viewBox="0 0 24 24" width="12" height="12"><rect x="6" y="6" width="12" height="12" fill="#DC3E3A"/></svg> Difícil</span>'
    else:
        return '<span class="tag-diff tag-medio"><svg viewBox="0 0 24 24" width="12" height="12"><rect x="6" y="5" width="4" height="14" fill="#E8C520"/><rect x="14" y="5" width="4" height="14" fill="#E8C520"/></svg> Médio</span>'

def render_aluno_view(preselected_quiz_code: str = None):
    render_brand_header("Simulador TRI", "Simulador TRI · Pré-Enem Digital MT")

    tab_responder, tab_consultar = st.tabs(["📝 Cartão-Resposta da Prova", "🔍 Consultar Meu Resultado"])

    # =========================================================================
    # ABA 1: RESPONDER QUESTIONÁRIO
    # =========================================================================
    with tab_responder:
        # Se foi passado um código de quiz na URL
        quiz = None
        if preselected_quiz_code:
            quiz = db.get_quiz_by_code(preselected_quiz_code)
        
        if not quiz:
            st.markdown("<p class='eyebrow-text' style='margin-top:10px;'>Acesso ao Questionário</p>", unsafe_allow_html=True)
            col_code, col_select = st.columns([1, 1])
            
            with col_code:
                code_input = st.text_input("Código do Quiz (6 caracteres):", placeholder="Ex: A1B2C3", key="aluno_quiz_code").strip().upper()
                if code_input:
                    quiz = db.get_quiz_by_code(code_input)
                    if not quiz:
                        st.error("Nenhum questionário encontrado com este código.")
            
            if not quiz:
                with col_select:
                    active_quizzes = [q for q in db.get_all_quizzes() if q['is_active']]
                    if active_quizzes:
                        q_map = {f"{q['title']} (Código: {q['quiz_code']})": q['quiz_code'] for q in active_quizzes}
                        chosen_label = st.selectbox("Ou selecione uma avaliação ativa:", ["-- Selecione --"] + list(q_map.keys()), key="aluno_select_quiz")
                        if chosen_label != "-- Selecione --":
                            quiz = db.get_quiz_by_code(q_map[chosen_label])

        if not quiz:
            st.markdown("""
            <div class="pre-card" style="text-align: center; padding: 30px;">
                <p style="font-size: 16px; color: var(--ink-soft); margin: 0;">
                    📷 <b>Aponte a câmera do seu celular</b> para o QR Code projetado pelo professor ou digite o código acima para iniciar a sua prova.
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif not quiz['is_active']:
            st.warning(f"O questionário '{quiz['title']}' está temporariamente fechado para novas respostas pelo professor.")
        else:
            quiz_id = quiz['id']
            quiz_details = db.get_quiz_details(quiz_id)
            questions = quiz_details.get('questions', [])

            if not questions:
                st.warning("Este questionário ainda não possui questões cadastradas.")
            else:
                # =====================================================================
                # RECUPERAÇÃO E PERSISTÊNCIA EM CACHE DO PIN ÚNICO DO ALUNO
                # (Camada 1: URL Query Params | Camada 2: Session State | Camada 3: LocalStorage)
                # =====================================================================
                pin_session_key = f"student_pin_assigned_{quiz_id}"
                url_pin = st.query_params.get("pin", None)
                
                if url_pin and len(str(url_pin).strip()) == 4:
                    assigned_pin = str(url_pin).strip()
                    st.session_state[pin_session_key] = assigned_pin
                elif pin_session_key in st.session_state:
                    assigned_pin = st.session_state[pin_session_key]
                    st.query_params["pin"] = assigned_pin
                    st.query_params["quiz"] = quiz['quiz_code']
                else:
                    assigned_pin = db.generate_unique_student_pin(quiz_id)
                    st.session_state[pin_session_key] = assigned_pin
                    st.query_params["pin"] = assigned_pin
                    st.query_params["quiz"] = quiz['quiz_code']

                # Sincronização com o localStorage do navegador (permanece mesmo se fechar a aba ou rescannear)
                st.components.v1.html(f"""
                <script>
                (function() {{
                    const quizId = "{quiz_id}";
                    const quizCode = "{quiz['quiz_code']}";
                    const currentPin = "{assigned_pin}";
                    const storageKey = 'pre_enem_pin_' + quizId;
                    
                    // Salva o PIN atual no localStorage do dispositivo do aluno
                    if (currentPin) {{
                        localStorage.setItem(storageKey, currentPin);
                    }}
                    
                    // Verifica se a URL perdeu o PIN mas o localStorage possui
                    const urlParams = new URLSearchParams(window.parent.location.search);
                    if (!urlParams.get('pin')) {{
                        const cachedPin = localStorage.getItem(storageKey);
                        if (cachedPin && cachedPin.length === 4) {{
                            urlParams.set('quiz', quizCode);
                            urlParams.set('pin', cachedPin);
                            window.parent.location.search = urlParams.toString();
                        }}
                    }}
                }})();
                </script>
                """, height=0, width=0)

                # Cartão de Identificação Único do Aluno (Design Oficial Pré-Enem)
                st.markdown(f"""
                <div class="pin-display-card">
                    <span class="eyebrow-text" style="color: var(--ink-soft); font-size: 13px;">🎫 SEU CÓDIGO IDENTIFICADOR ÚNICO (SALVO EM CACHE)</span>
                    <div>
                        <div class="pin-number">{assigned_pin}</div>
                    </div>
                    <p style="margin: 4px 0 0; color: var(--ink-soft); font-size: 14px;">
                        📸 <b>Código fixado e salvo no seu navegador!</b> Mesmo que você atualize a página ou feche o aplicativo, seu código permanecerá <b>{assigned_pin}</b>.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                # Cabeçalho do Quiz
                st.markdown(f"""
                <div class="pre-card" style="margin-bottom: 20px;">
                    <h2 style="margin: 0 0 6px 0; color: var(--ink);">{quiz['title']}</h2>
                    <p style="color: var(--ink-soft); margin: 0 0 10px 0;">{quiz['description'] or 'Avaliação com cálculo de proficiência Teoria de Resposta ao Item (TRI - Padrão ENEM).'}</p>
                    <span class="eyebrow-text">Total: {len(questions)} Questões | Tempo sugerido: {quiz['time_limit_minutes'] or 'Livre'} min</span>
                </div>
                """, unsafe_allow_html=True)

                # Identificação Opcional
                student_name = st.text_input("Seu Nome (Opcional - caso queira se identificar na lista do professor):", placeholder="Ex: Maria Eduarda (Opcional)", key=f"name_{quiz_id}")

                st.markdown("<p class='eyebrow-text' style='margin-top: 20px;'>Questões da Prova</p>", unsafe_allow_html=True)

                # Dicionário para armazenar as seleções do aluno
                selected_answers = {}

                for idx, q in enumerate(questions, 1):
                    badge_html = get_difficulty_badge_html(q.get('difficulty_level', 'Média'))
                    
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
                        <span style="font-family: var(--font-mono); font-weight: 700; font-size: 13px; color: var(--ink-soft);">QUESTÃO {idx} DE {len(questions)}</span>
                        {badge_html}
                    </div>
                    <div style="font-size: 16px; font-weight: 600; color: var(--ink); line-height: 1.5; margin: 8px 0 12px 0;">
                        {q['question_text']}
                    </div>
                    """, unsafe_allow_html=True)

                    # Exibe imagem ilustrativa da questão se houver
                    if q.get('image_data'):
                        st.image(q['image_data'], caption=f"Ilustração - Questão {idx}", use_container_width=True)

                    # Mapeia as opções
                    options_dict = {f"{opt['option_text']}": opt['id'] for opt in q['options']}
                    
                    # Widget de seleção (Radio)
                    choice = st.radio(
                        f"Selecione sua resposta para a questão {idx}:",
                        options=list(options_dict.keys()),
                        index=None,
                        key=f"q_{q['id']}",
                        label_visibility="collapsed"
                    )
                    
                    if choice:
                        selected_answers[q['id']] = options_dict[choice]

                    st.markdown("<hr style='border: none; border-top: 2px dashed var(--line); margin: 20px 0;'>", unsafe_allow_html=True)

                # Botão de Envio
                respondidas_count = len(selected_answers)
                total_q_count = len(questions)
                st.markdown(f"<p class='eyebrow-text' style='text-align: right;'>{respondidas_count}/{total_q_count} questões respondidas</p>", unsafe_allow_html=True)

                if st.button("Enviar Minhas Respostas", type="primary", use_container_width=True):
                    unanswered = len(questions) - len(selected_answers)
                    if unanswered > 0:
                        st.warning(f"Você ainda não respondeu {unanswered} questão(ões). Por favor, responda todas antes de enviar.")
                        st.stop()

                    # Registrar no banco de dados SQLite com cálculo seguro da TRI e o PIN único
                    with st.spinner("Gravando suas respostas no sistema..."):
                        result = db.submit_student_answers(
                            quiz_id=quiz_id,
                            student_pin=assigned_pin,
                            student_name=student_name,
                            student_identifier=f"PIN-{assigned_pin}",
                            selected_options=selected_answers
                        )

                    # Verificar se o professor já liberou as notas ou se estão sob sigilo durante a prova
                    is_released = bool(quiz.get('results_released'))
                    
                    if not is_released:
                        # =========================================================
                        # MODO SEGURO: NOTAS E RESPOSTAS OCULTAS
                        # =========================================================
                        st.success("🎉 **Suas respostas foram enviadas e registradas com sucesso!**")
                        st.markdown(f"""
                        <div class="pre-card" style="border: 2px solid var(--teal); background: var(--paper-tint); margin-top: 15px;">
                            <p class="eyebrow-text">Avaliação em Andamento</p>
                            <h2 style="color: var(--ink); margin-top: 0;">Respostas Registradas!</h2>
                            <p style="font-size: 16px; color: var(--ink); line-height: 1.6;">
                                🎫 <b>Seu Código de Acesso Único:</b> <span style="font-family: var(--font-mono); font-size: 24px; font-weight: 800; color: var(--teal-dark);">{assigned_pin}</span>
                            </p>
                            <p style="color: var(--ink-soft); font-size: 14.5px; line-height: 1.6;">
                                Por critério pedagógico e para garantir o sigilo da avaliação enquanto a turma responde, <b>o gabarito e a sua nota TRI só serão divulgados após todos terminarem e o professor liberar as notas</b>.
                            </p>
                            <p style="color: var(--ink); font-size: 14px; margin-bottom: 0;">
                                📌 <i>Guarde o código <b>{assigned_pin}</b> e consulte seu boletim oficial na aba <b>'Consultar Meu Resultado'</b> assim que o professor encerrar a prova.</i>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Se já estava liberado pelo professor
                        st.success("Suas respostas foram avaliadas!")
                        tri_score = result.get('tri_score', 500.0)
                        theta = result.get('theta', 0.0)
                        coherence_label = result.get('coherence_label', 'Coerente')
                        
                        st.markdown(f"""
                        <div class="score-reveal-box" style="margin-top: 15px;">
                            <p class="score-label">Nota TRI Simulada (Escala ENEM)</p>
                            <div class="score-big">{tri_score:.0f}</div>
                            <div class="score-msg">Proficiência: {theta:+.2f} θ · {coherence_label}</div>
                        </div>
                        """, unsafe_allow_html=True)

    # =========================================================================
    # ABA 2: CONSULTAR RESULTADO / BOLETIM (VIA CÓDIGO DE 4 DÍGITOS)
    # =========================================================================
    with tab_consultar:
        st.markdown("<p class='eyebrow-text' style='margin-top:10px;'>Consulta de Boletim</p>", unsafe_allow_html=True)
        st.markdown("Digite o seu código de **4 números** gerado ao acessar a prova para visualizar sua nota oficial:")
        
        all_quizzes = db.get_all_quizzes()
        if not all_quizzes:
            st.info("Nenhum questionário cadastrado no momento.")
        else:
            q_options = {f"{q['title']} (Código: {q['quiz_code']})": q for q in all_quizzes}
            selected_label_c = st.selectbox("Selecione a Avaliação:", list(q_options.keys()), key="consult_quiz_select")
            selected_quiz_c = q_options[selected_label_c]
            
            search_pin_input = st.text_input("Digite o seu Código Único (4 dígitos ou Nome cadastrado):", max_chars=20, placeholder="Ex: 4829", key="search_student_pin_input")
            
            if st.button("Consultar Meu Resultado", type="primary", use_container_width=True):
                if not search_pin_input.strip():
                    st.error("Por favor, digite seu código de 4 números para consultar.")
                else:
                    # Verificar se as notas já foram liberadas pelo professor
                    if not selected_quiz_c.get('results_released'):
                        st.warning("⏳ **Avaliação ainda em andamento.**")
                        st.info("O professor ainda não liberou a divulgação das notas e gabaritos deste questionário. Aguarde o encerramento da prova por toda a turma.")
                    else:
                        # Buscar submissão pelo PIN de 4 dígitos
                        sub_data = db.get_student_submission_by_credentials(selected_quiz_c['id'], search_pin_input)
                        
                        if not sub_data:
                            st.error(f"Nenhum registro de resposta encontrado para o código '{search_pin_input}' neste questionário. Verifique se digitou o código de 4 números correto.")
                        else:
                            pin_display = sub_data.get('student_pin') or search_pin_input
                            tri_val = sub_data['tri_score']
                            score_val = sub_data['score']
                            tot_val = sub_data['total_points']
                            theta_val = sub_data['theta']
                            
                            # Score Message Tier
                            if tri_val >= 700:
                                tier_msg = "Mandou muito bem! Continue nesse ritmo."
                                tier_color = "var(--teal)"
                            elif tri_val >= 450:
                                tier_msg = "Bom caminho! Reforce os pontos que errou."
                                tier_color = "var(--yellow-dark)"
                            else:
                                tier_msg = "Hora de treinar mais esse conteúdo. Você chega lá!"
                                tier_color = "var(--coral)"

                            st.markdown(f"""
                            <div class="score-reveal-box" style="margin: 15px 0 20px 0;">
                                <p class="score-label">Resultado Oficial · Aluno #{pin_display}</p>
                                <div class="score-big">{tri_val:.0f}</div>
                                <div class="score-label">Nota TRI Simulada (Escala ENEM) · {score_val:.0f}/{tot_val:.0f} Acertos</div>
                                <div class="score-msg" style="color: {tier_color};">{tier_msg}</div>
                                <p style="font-family: var(--font-mono); font-size: 13px; color: var(--ink-soft); margin-top: 10px;">Proficiência Estimada: {theta_val:+.2f} θ | Coerência Pedagógica: {sub_data.get('coherence_label', 'Coerente')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Detalhamento do Gabarito Comentado
                            with st.expander("📝 Ver Gabarito Comentado e Explicações", expanded=True):
                                for idx, ans_item in enumerate(sub_data.get('answers', []), 1):
                                    is_hit = bool(ans_item['is_correct'])
                                    status_label = "✅ [Acertou]" if is_hit else "❌ [Errou]"
                                    diff_badge = get_difficulty_badge_html(ans_item.get('difficulty_level', 'Média'))
                                    
                                    st.markdown(f"""
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                                        <span style="font-family: var(--font-mono); font-weight: 700; font-size: 13px; color: var(--ink);">{status_label} Questão {idx}</span>
                                        {diff_badge}
                                    </div>
                                    <div style="font-size: 15px; font-weight: 600; color: var(--ink); margin: 6px 0;">{ans_item['question_text']}</div>
                                    """, unsafe_allow_html=True)

                                    if ans_item.get('image_data'):
                                        st.image(ans_item['image_data'], caption=f"Ilustração - Questão {idx}", width=300)
                                    
                                    st.markdown(f"- **Sua resposta:** {ans_item['selected_option_text'] or 'Não respondida'}")
                                    if not is_hit:
                                        st.markdown(f"- **Resposta correta:** <span style='color: var(--teal-dark); font-weight: 700;'>{ans_item['correct_option_text']}</span>", unsafe_allow_html=True)
                                    if ans_item.get('explanation'):
                                        st.caption(f"**Explicação Pedagógica:** {ans_item['explanation']}")
                                    st.markdown("<hr style='border: none; border-top: 1px solid var(--line); margin: 12px 0;'>", unsafe_allow_html=True)



