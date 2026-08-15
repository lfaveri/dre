import streamlit as st
import qrcode
import io
import socket
import base64
from PIL import Image
import database as db
from theme_pre_enem import render_brand_header

def get_local_ip():
    """Tenta identificar o IP local da máquina na rede Wi-Fi/Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def generate_qr_image(url: str) -> bytes:
    """Gera os bytes de uma imagem PNG com o QR Code de alta qualidade nas cores oficiais."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0C535E", back_color="#FFFFFF")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def render_professor_view():
    render_brand_header("Área do Professor", "Simulador TRI · Pré-Enem Digital MT")
    st.markdown("<p style='color:var(--ink-soft); margin-top:-6px;'>Cadastre questões, defina dificuldades para a TRI, ative a prova e gere QR Codes para os estudantes.</p>", unsafe_allow_html=True)
    
    tabs = st.tabs(["📚 Quizzes & QR Codes", "➕ Criar Nova Avaliação", "✏️ Cadastrar Questões", "⚙️ Segurança & Senha"])

    # =========================================================================
    # TAB 1: MEUS QUIZZES & QR CODES
    # =========================================================================
    with tabs[0]:
        st.subheader("Questionários Cadastrados")
        quizzes = db.get_all_quizzes()
        
        if not quizzes:
            st.info("Nenhum quiz cadastrado ainda. Use a aba 'Criar Novo Quiz' para começar!")
        else:
            local_ip = get_local_ip()
            
            for q in quizzes:
                with st.expander(f"**{q['title']}** (Código: `{q['quiz_code']}`) — {q['question_count']} questões | {q['submission_count']} respostas", expanded=False):
                    col1, col2 = st.columns([1.2, 1])
                    
                    with col1:
                        st.markdown(f"**Descrição:** {q['description'] or '_Sem descrição_'}")
                        st.markdown(f"**Criado em:** {q['created_at']}")
                        status_str = "🟢 **Recebendo Respostas**" if q['is_active'] else "⏸️ **Pausado / Fechado**"
                        status_res = "📢 **Notas Liberadas aos Alunos**" if q.get('results_released') else "🔒 **Notas Ocultas (Em andamento)**"
                        st.markdown(f"**Status:** {status_str} | {status_res}")
                        
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            if q['is_active']:
                                if st.button("Pausar Quiz", key=f"pause_{q['id']}", use_container_width=True):
                                    db.toggle_quiz_status(q['id'], False)
                                    st.rerun()
                            else:
                                if st.button("Ativar Quiz", key=f"activate_{q['id']}", use_container_width=True):
                                    db.toggle_quiz_status(q['id'], True)
                                    st.rerun()
                        
                        with col_btn2:
                            if q.get('results_released'):
                                if st.button("🔒 Ocultar Notas", key=f"hide_res_{q['id']}", use_container_width=True, help="Oculta as notas e o gabarito para os alunos."):
                                    db.toggle_quiz_results_release(q['id'], False)
                                    st.rerun()
                            else:
                                if st.button("📢 Liberar Notas", key=f"rel_res_{q['id']}", type="primary", use_container_width=True, help="Libera as notas TRI e gabaritos comentados para os alunos após o término da aplicação."):
                                    db.toggle_quiz_results_release(q['id'], True)
                                    st.success("Notas liberadas com sucesso para os alunos!")
                                    st.rerun()
                        
                        with col_btn3:
                            if st.button("Excluir", key=f"del_{q['id']}", type="secondary", use_container_width=True):
                                db.delete_quiz(q['id'])
                                st.success("Quiz excluído com sucesso!")
                                st.rerun()

                        st.divider()
                        st.markdown("#### Link de Acesso do Aluno")
                        
                        # URL padrão configurada para o deploy oficial
                        base_url_default = "https://questions-and-anwers.streamlit.app"
                        base_url = st.text_input(
                            "Endereço Base do Aplicativo (Deploy ou IP Local):",
                            value=base_url_default,
                            key=f"url_base_{q['id']}",
                            help="URL pública onde o app está hospedado. Altere caso queira testar em rede local."
                        )
                        
                        clean_base = base_url.rstrip('/')
                        quiz_url = f"{clean_base}/?quiz={q['quiz_code']}"
                        st.code(quiz_url, language="text")

                    with col2:
                        st.markdown("#### QR Code para Sala de Aula")
                        qr_bytes = generate_qr_image(quiz_url)
                        st.image(qr_bytes, caption=f"Escaneie para responder: {q['title']}", width=230)
                        
                        st.download_button(
                            label="Baixar Imagem do QR Code (PNG)",
                            data=qr_bytes,
                            file_name=f"qrcode_quiz_{q['quiz_code']}.png",
                            mime="image/png",
                            key=f"dl_{q['id']}",
                            use_container_width=True
                        )

    # =========================================================================
    # TAB 2: CRIAR NOVO QUIZ
    # =========================================================================
    with tabs[1]:
        st.subheader("Cadastrar Novo Questionário")
        with st.form("form_create_quiz", clear_on_submit=True):
            title = st.text_input("Título do Quiz *", placeholder="Ex: Avaliação de Física - Cinemática")
            description = st.text_area("Descrição / Instruções para os Alunos", placeholder="Ex: Responda a todas as questões individualmente. Boa sorte!")
            time_limit = st.number_input("Tempo Estimado (minutos - opcional)", min_value=0, max_value=180, value=0, help="0 significa sem limite de tempo estrito.")
            
            submitted = st.form_submit_button("Salvar Quiz", use_container_width=True, type="primary")
            if submitted:
                if not title.strip():
                    st.error("Por favor, preencha o título do Quiz!")
                else:
                    new_q = db.create_quiz(title, description, time_limit)
                    st.success(f"Quiz '{title}' criado com sucesso! Código gerado: {new_q['quiz_code']}")
                    st.info("Agora vá para a aba 'Adicionar Questões' para cadastrar as perguntas!")

    # =========================================================================
    # TAB 3: ADICIONAR QUESTÕES (COM SUPORTE A IMAGENS E TRI ENEM)
    # =========================================================================
    with tabs[2]:
        st.subheader("Adicionar Perguntas ao Quiz")
        quizzes = db.get_all_quizzes()
        
        if not quizzes:
            st.warning("Crie primeiro um Quiz na aba anterior.")
        else:
            quiz_options = {f"{q['title']} (Código: {q['quiz_code']})": q['id'] for q in quizzes}
            selected_quiz_label = st.selectbox("Selecione o Quiz de Destino:", list(quiz_options.keys()))
            selected_quiz_id = quiz_options[selected_quiz_label]

            # Mostrar questões atuais do quiz selecionado
            quiz_data = db.get_quiz_details(selected_quiz_id)
            existing_questions = quiz_data.get('questions', [])
            
            st.markdown(f"**Questões atuais neste quiz:** {len(existing_questions)}")
            if existing_questions:
                with st.expander("Ver Questões já cadastradas e Calibração TRI", expanded=False):
                    for idx, q_item in enumerate(existing_questions, 1):
                        diff_badge = "🟢 Fácil" if q_item.get('difficulty_level') == 'Fácil' else ("🔴 Difícil" if q_item.get('difficulty_level') == 'Difícil' else "🟡 Média")
                        st.markdown(f"**{idx}. {q_item['question_text']}** — {diff_badge} ({q_item['points']} pts)")
                        
                        param_info = f"Parâmetros TRI (Modelo 3PL): Dificuldade (b) = `{q_item.get('param_b', 0.0)}` | Discriminação (a) = `{q_item.get('param_a', 1.2)}` | Chute (c) = `{q_item.get('param_c', 0.25)}`"
                        st.caption(param_info)

                        if q_item.get('image_data'):
                            st.image(q_item['image_data'], caption=f"Imagem da Questão {idx}", width=320)
                        for opt in q_item['options']:
                            mark = "[Correta]" if opt['is_correct'] else "[Incorreta]"
                            st.write(f"{mark} {opt['option_text']}")
                        if q_item.get('explanation'):
                            st.caption(f"Explicação Pedagógica: {q_item['explanation']}")
                        st.divider()

            st.markdown("---")
            st.markdown("#### Formulário da Nova Questão")

            with st.form("form_add_question", clear_on_submit=True):
                question_text = st.text_area("Enunciado da Questão *", placeholder="Ex: Analise o gráfico/imagem abaixo e assinale a alternativa correta:")
                
                # Campo de Upload de Imagem
                uploaded_img = st.file_uploader(
                    "Imagem Ilustrativa para a Questão (Opcional - PNG, JPG, JPEG, WEBP):",
                    type=["png", "jpg", "jpeg", "webp"],
                    help="Caso a questão dependa de um gráfico, diagrama, foto ou mapa, faça o upload aqui."
                )

                col_pts, col_diff = st.columns(2)
                with col_pts:
                    points = st.number_input("Pontuação Clássica", min_value=0.5, max_value=100.0, value=2.5, step=0.5)
                with col_diff:
                    diff_choice = st.selectbox(
                        "Nível de Dificuldade Pedagógica (Escada do ENEM):",
                        ["Média (Degrau Intermediário)", "Fácil (Degrau Base)", "Difícil (Degrau do Topo)"],
                        help="A TRI utiliza esta classificação para identificar a coerência das respostas dos alunos."
                    )

                # Extrair label limpo
                if "Fácil" in diff_choice:
                    clean_diff = "Fácil"
                    default_b = -1.2
                    default_a = 1.2
                elif "Difícil" in diff_choice:
                    clean_diff = "Difícil"
                    default_b = 1.4
                    default_a = 1.6
                else:
                    clean_diff = "Média"
                    default_b = 0.0
                    default_a = 1.4

                # Seção de Calibração Avançada TRI
                with st.expander("⚙️ Calibração Avançada dos Parâmetros TRI (Modelo 3PL)", expanded=False):
                    st.caption("Ajuste fino dos pesos do modelo psicométrico do ENEM (opcional):")
                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        param_b = st.slider("Dificuldade (b):", min_value=-3.0, max_value=3.0, value=float(default_b), step=0.1, help="Valores negativos = questões fáceis; positivos = questões difíceis.")
                    with col_p2:
                        param_a = st.slider("Discriminação (a):", min_value=0.5, max_value=2.5, value=float(default_a), step=0.1, help="Capacidade da questão de separar alunos com alto e baixo domínio.")
                    with col_p3:
                        param_c = st.slider("Acerto Casual / Chute (c):", min_value=0.0, max_value=0.40, value=0.25, step=0.05, help="Probabilidade estimada de acerto ao acaso.")

                explanation = st.text_input("Explicação Pedagógica (Feedback ao Aluno pós-envio)", placeholder="Ex: Vm = ΔS / Δt")
                
                st.markdown("**Alternativas de Resposta (Marque a Correta):**")
                
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    opt_a = st.text_input("Alternativa A *", placeholder="Texto da opção A")
                with col_b:
                    is_correct_a = st.checkbox("Correta (A)", value=True, key="chk_a")

                col_a, col_b = st.columns([4, 1])
                with col_a:
                    opt_b = st.text_input("Alternativa B *", placeholder="Texto da opção B")
                with col_b:
                    is_correct_b = st.checkbox("Correta (B)", value=False, key="chk_b")

                col_a, col_b = st.columns([4, 1])
                with col_a:
                    opt_c = st.text_input("Alternativa C (Opcional)", placeholder="Texto da opção C")
                with col_b:
                    is_correct_c = st.checkbox("Correta (C)", value=False, key="chk_c")

                col_a, col_b = st.columns([4, 1])
                with col_a:
                    opt_d = st.text_input("Alternativa D (Opcional)", placeholder="Texto da opção D")
                with col_b:
                    is_correct_d = st.checkbox("Correta (D)", value=False, key="chk_d")

                btn_add_q = st.form_submit_button("Salvar Questão", use_container_width=True, type="primary")

                if btn_add_q:
                    if not question_text.strip():
                        st.error("Digite o enunciado da questão!")
                    elif not opt_a.strip() or not opt_b.strip():
                        st.error("Preencha ao menos as alternativas A e B!")
                    else:
                        options_list = [
                            {"text": opt_a.strip(), "is_correct": is_correct_a},
                            {"text": opt_b.strip(), "is_correct": is_correct_b}
                        ]
                        if opt_c.strip():
                            options_list.append({"text": opt_c.strip(), "is_correct": is_correct_c})
                        if opt_d.strip():
                            options_list.append({"text": opt_d.strip(), "is_correct": is_correct_d})

                        correct_count = sum(1 for o in options_list if o['is_correct'])
                        if correct_count != 1:
                            st.error("Selecione exatamente UMA alternativa como correta!")
                        else:
                            # Processar imagem se foi enviada
                            image_b64_data = None
                            if uploaded_img is not None:
                                mime_type = uploaded_img.type or "image/png"
                                raw_bytes = uploaded_img.read()
                                b64_str = base64.b64encode(raw_bytes).decode("utf-8")
                                image_b64_data = f"data:{mime_type};base64,{b64_str}"

                            db.add_question(
                                quiz_id=selected_quiz_id,
                                question_text=question_text.strip(),
                                points=points,
                                explanation=explanation.strip(),
                                options=options_list,
                                image_data=image_b64_data,
                                param_a=param_a,
                                param_b=param_b,
                                param_c=param_c,
                                difficulty_level=clean_diff
                            )
                            st.success("Questão cadastrada e calibrada na TRI com sucesso!")
                            st.rerun()

    # =========================================================================
    # TAB 4: SEGURANÇA E SENHA DO PROFESSOR
    # =========================================================================
    with tabs[3]:
        st.subheader("Segurança e Senha de Acesso")
        st.markdown("Defina a senha necessária para acessar o Painel do Professor e o Dashboard de Resultados.")
        
        with st.form("form_change_password"):
            current_pwd = st.text_input("Senha Atual", type="password")
            new_pwd = st.text_input("Nova Senha", type="password", help="Mínimo de 4 caracteres.")
            confirm_pwd = st.text_input("Confirmar Nova Senha", type="password")
            
            submit_pwd = st.form_submit_button("Atualizar Senha", use_container_width=True, type="primary")
            if submit_pwd:
                saved_pwd = db.get_professor_password()
                if current_pwd != saved_pwd:
                    st.error("A senha atual informada está incorreta.")
                elif len(new_pwd) < 4:
                    st.error("A nova senha deve possuir pelo menos 4 caracteres.")
                elif new_pwd != confirm_pwd:
                    st.error("A confirmação da nova senha não confere.")
                else:
                    db.set_professor_password(new_pwd)
                    st.success("Senha do professor atualizada com sucesso!")

