# Quiz Interativo com Streamlit, SQLite e QR Code

Sistema completo e moderno para criação de questionários/quizzes interativos para professores e salas de aula, com geração automática de **QR Code** para resposta dos alunos via smartphone e **Dashboard dinâmico em tempo real** com gráficos analíticos.

---

## Funcionalidades Principais

- **Sistema TRI Padrão ENEM (Teoria de Resposta ao Item - Modelo 3PL)**:
  - **Cálculo da Proficiência ($\theta$)**: Estimador EAP (*Expected A Posteriori*) na escala oficial do ENEM (centro em 500 pontos, desvio 100).
  - **Escada de Conhecimento e Coerência Pedagógica**: O sistema analisa o caderno inteiro de respostas do aluno. Acertos em questões difíceis com erros nas fáceis são penalizados como chutes.
  - **Parâmetros Psicométricos ($a, b, c$)**: Calibração de Dificuldade ($b$), Discriminação ($a$) e Probabilidade de Chute ($c$) por questão.
  - **Curvas Características dos Itens (CCI)**: Gráficos psicométricos interativos em formato "S" (Plotly) no Dashboard.
- **Área do Professor (Protegida por Senha)**:
  - Cadastro rápido de questionários (título, instruções, tempo limite).
  - Adição de questões com **suporte a imagens ilustrativas** e **seletor pedagógico TRI** (Fácil, Média, Difícil ou calibração avançada com sliders).
  - Pontuação personalizada e gabarito com explicação pedagógica comentada.
  - Aba de **Configuração de Senha** para personalizar o PIN de acesso do docente (senha padrão inicial: `admin123`).
- **Gerador de QR Code Inteligente**:
  - Geração automática do QR Code com o link direto do quiz (`https://questions-and-anwers.streamlit.app/?quiz=CODIGO`).
  - Detecção automática do IP da rede local para uso em sala de aula (Wi-Fi).
  - Download da imagem do QR Code em alta resolução (PNG) para projeção ou slides.
- **Portal do Aluno (Totalmente Isolado)**:
  - Visualização exclusiva do questionário, sem acesso a dados de outros alunos ou painéis administrativos.
  - Exibição da **Nota TRI (Escala ENEM)**, proficiência ($\theta$) e **Badge de Coerência Pedagógica** após o envio.
  - Interface limpa, responsiva e adaptada para celulares e tablets com suporte a imagens.
  - Acesso direto via câmera/QR Code ou código de 6 dígitos.
- **Dashboard Dinâmico de Resultados & Psicométrico**:
  - **Métricas TRI em tempo real**: Média TRI (ENEM), proficiência média ($\theta$), maior/menor nota TRI e aproveitamento.
  - **Gráfico de Dispersão Coerência vs. TRI**: Efeito visual dos acertos casuais comparando % clássica vs. Nota TRI.
  - **Curvas Características dos Itens (CCI)** e análise de distratores.
  - **Ranking da Turma por Nota TRI**: Com exportação completa em **CSV (Excel)**.

---

## Estrutura do Projeto

```text
quiz_interativo_streamlit/
├── .streamlit/
│   └── config.toml          # Configurações de tema e servidor
├── modules/
│   ├── professor.py         # Criação de quizzes, questões e geração de QR Code
│   ├── aluno.py             # Interface responsiva para o aluno responder
│   └── dashboard.py         # Dashboard interativo com gráficos Plotly e ranking
├── app.py                   # Ponto de entrada e roteamento via URL params
├── database.py              # Camada de persistência SQLite e queries analíticas
├── requirements.txt         # Lista de dependências Python
├── .gitignore               # Arquivos ignorados pelo Git
└── README.md                # Documentação do projeto
```

---

## Como Executar Localmente

### 1. Pré-requisitos
Tenha o **Python 3.9+** instalado no seu computador.

### 2. Clonar ou Baixar o Projeto
Abra o terminal/PowerShell na pasta do projeto:
```bash
cd quiz_interativo_streamlit
```

### 3. Criar e Ativar um Ambiente Virtual (Recomendado)
```bash
# No Windows:
python -m venv venv
.\venv\Scripts\activate

# No Linux/Mac:
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar as Dependências
```bash
pip install -r requirements.txt
```

### 5. Iniciar a Aplicação
```bash
streamlit run app.py
```

O Streamlit abrirá automaticamente no navegador em: `http://localhost:8501`.

---

## Como Usar com Alunos na Mesma Rede Wi-Fi (Sala de Aula)

Ao executar o comando `streamlit run app.py`, o terminal exibirá duas URLs:
1. **Local URL:** `http://localhost:8501` (Acesso no seu próprio computador)
2. **Network URL:** `http://192.168.x.x:8501` (Acesso dos celulares na mesma rede)

No painel do professor, o sistema também permite alterar o endereço base para o IP local se desejado.

---

## Como Publicar Gratuitamente no Streamlit Community Cloud

Para que os alunos possam responder de qualquer lugar (mesmo usando dados móveis 4G/5G):

1. Suba este projeto para um repositório no **GitHub** (veja as instruções abaixo).
2. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com sua conta do GitHub.
3. Clique em **"New app"**, selecione o repositório, a branch `main` e o arquivo principal `app.py`.
4. Defina o App URL personalizado como `questions-and-anwers.streamlit.app` e clique em **"Deploy!"**.
5. Em poucos segundos, sua aplicação estará no ar no link oficial: `https://questions-and-anwers.streamlit.app/`.
6. O sistema já vem configurado por padrão com este link para gerar automaticamente os QR Codes dos alunos (`https://questions-and-anwers.streamlit.app/?quiz=CODIGO`)!

---

## Como Fazer Upload para o GitHub

Execute os comandos no terminal dentro da pasta do projeto:

```bash
# 1. Inicializar o repositório git
git init

# 2. Adicionar todos os arquivos
git add .

# 3. Criar o primeiro commit
git commit -m "feat: Aplicativo de Quiz Interativo com Streamlit, SQLite e QR Code"

# 4. Criar a branch principal
git branch -M main

# 5. Conectar com o seu repositório remoto do GitHub
# (Substitua SEU-USUARIO e SEU-REPOSITORIO pelos seus dados)
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git

# 6. Enviar os arquivos
git push -u origin main
```

---

## Licença
Este projeto está sob a licença MIT. Sinta-se livre para usar, modificar e distribuir.
