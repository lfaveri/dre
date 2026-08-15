import streamlit as st
import database as db
from theme_pre_enem import inject_custom_theme, LOGO_PRE_ENEM_BASE64, LOGO_SEDUC_DRE_BASE64
from modules.professor import render_professor_view
from modules.aluno import render_aluno_view
from modules.dashboard import render_dashboard_view

# Configuração global da página (Menu Lateral começa fechado por padrão)
st.set_page_config(
    page_title="Simulador TRI · Pré-Enem Digital MT",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Injeta CSS e Design System Oficial do Pré-Enem Digital MT
inject_custom_theme()

# Inicializa o banco SQLite e popula dados de exemplo se necessário
db.seed_sample_quiz_if_empty()

# Estado de autenticação do professor na sessão
if "professor_auth" not in st.session_state:
    st.session_state.professor_auth = False

# Leitura de parâmetros de URL para acesso direto via QR Code
query_params = st.query_params
url_quiz_code = query_params.get("quiz", None)

# Barra Lateral de Navegação e Controle de Acesso
with st.sidebar:
    st.markdown(f'''
    <div style="text-align: center; margin-bottom: 14px;">
        <img src="{LOGO_PRE_ENEM_BASE64}" style="width: 100%; max-width: 190px; margin-bottom: 10px;" alt="Pré-Enem Digital MT">
        <img src="{LOGO_SEDUC_DRE_BASE64}" style="width: 100%; max-width: 190px; border-radius: 6px;" alt="SEDUC MT - DRE Primavera do Leste">
    </div>
    ''', unsafe_allow_html=True)
    st.markdown("<p style='font-family:IBM Plex Mono, monospace; font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#9FD3D3; text-align:center;'>Pré-Enem Digital MT · DRE</p>", unsafe_allow_html=True)
    
    if st.session_state.professor_auth:
        st.success("Professor Conectado")
        
        nav_options = [
            "Área do Professor",
            "Dashboard de Resultados",
            "Portal do Aluno (Simulação)"
        ]
        
        selected_page = st.radio(
            "Navegação:",
            nav_options,
            index=0
        )
        
        st.divider()
        if st.button("Sair da Conta (Logout)", type="secondary", use_container_width=True):
            st.session_state.professor_auth = False
            st.rerun()
            
    else:
        # Visão restrita para Alunos
        st.caption("Portal do Estudante")
        st.markdown("""
        **Bem-vindo(a)!**
        - Responda às perguntas com atenção.
        - Assegure-se de preencher seu nome antes de enviar.
        - Ao finalizar, confira sua nota e explicações.
        """)
        
        st.divider()
        with st.expander("Acesso do Professor 🔒", expanded=False):
            st.caption("Área restrita a docentes e administradores.")
            with st.form("sidebar_login_form"):
                pwd_input = st.text_input("Senha de Acesso:", type="password", placeholder="Digite sua senha")
                login_btn = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                
                if login_btn:
                    current_master_pwd = db.get_professor_password()
                    if pwd_input == current_master_pwd:
                        st.session_state.professor_auth = True
                        st.success("Acesso liberado!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta!")
        
        selected_page = "Portal do Aluno"

# Roteamento Seguro de Páginas
if not st.session_state.professor_auth:
    # Apenas o questionário é renderizado para os alunos
    render_aluno_view(preselected_quiz_code=url_quiz_code)
else:
    # Roteamento completo para o professor autenticado
    if selected_page == "Área do Professor":
        render_professor_view()
    elif selected_page == "Dashboard de Resultados":
        render_dashboard_view()
    elif selected_page == "Portal do Aluno (Simulação)":
        render_aluno_view(preselected_quiz_code=url_quiz_code)
