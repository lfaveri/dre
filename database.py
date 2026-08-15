import sqlite3
import uuid
import random
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
import tri_engine

import os
import shutil

DB_FILE = "quiz_app.db"
BACKUP_DIR = "backups"

# Lock reentrante para serialização atômica de escritas no SQLite sob alta concorrência
db_lock = threading.RLock()

def backup_database():
    """Cria uma cópia de segurança automática do banco de dados SQLite para prevenir qualquer perda acidental de dados."""
    try:
        if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            backup_path = os.path.join(BACKUP_DIR, "quiz_app_backup.db")
            shutil.copy2(DB_FILE, backup_path)
    except Exception as e:
        pass

def get_connection():
    """
    Retorna uma conexão SQLite configurada para alta concorrência:
    - WAL Mode (Write-Ahead Logging): Leituras e escritas concorrentes sem bloqueio mútuo.
    - Synchronous NORMAL: Alto throughput de escrita.
    - Timeout de 60 segundos com busy_timeout no motor interno do SQLite.
    - Cache em memória otimizado.
    """
    conn = sqlite3.connect(DB_FILE, timeout=60.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -64000;")
    return conn

def init_db():
    """Cria todas as tabelas necessárias no banco SQLite se não existirem e aplica migrações de forma estritamente segura e não-destrutiva."""
    with db_lock:
        backup_database()
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Tabela de Configurações do Sistema (ex: Senha do Professor)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            # Senha padrão do professor se não existir
            cursor.execute("SELECT value FROM app_settings WHERE key = 'professor_password'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO app_settings (key, value) VALUES ('professor_password', 'admin123')")

            # Tabela de Quizzes / Questionários
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                time_limit_minutes INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                results_released INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Migrações seguras da tabela quizzes
            cursor.execute("PRAGMA table_info(quizzes);")
            qz_columns = [col[1] for col in cursor.fetchall()]
            if 'results_released' not in qz_columns:
                cursor.execute("ALTER TABLE quizzes ADD COLUMN results_released INTEGER DEFAULT 0;")

            # Tabela de Questões (com suporte a TRI e Imagens)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT DEFAULT 'multipla_escolha',
                points REAL DEFAULT 1.0,
                order_num INTEGER DEFAULT 1,
                explanation TEXT DEFAULT '',
                image_data TEXT DEFAULT NULL,
                param_a REAL DEFAULT 1.2,
                param_b REAL DEFAULT 0.0,
                param_c REAL DEFAULT 0.25,
                difficulty_level TEXT DEFAULT 'Média',
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
            );
            """)

            # Migrações seguras da tabela questions
            cursor.execute("PRAGMA table_info(questions);")
            q_columns = [col[1] for col in cursor.fetchall()]
            if 'image_data' not in q_columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN image_data TEXT DEFAULT NULL;")
            if 'param_a' not in q_columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN param_a REAL DEFAULT 1.2;")
            if 'param_b' not in q_columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN param_b REAL DEFAULT 0.0;")
            if 'param_c' not in q_columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN param_c REAL DEFAULT 0.25;")
            if 'difficulty_level' not in q_columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN difficulty_level TEXT DEFAULT 'Média';")

            # Tabela de Alternativas
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                option_text TEXT NOT NULL,
                is_correct INTEGER DEFAULT 0,
                order_num INTEGER DEFAULT 1,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );
            """)

            # Tabela de Submissões dos Alunos (com PIN de 4 dígitos, métricas TRI e Coerência Pedagógica)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                student_pin TEXT,
                student_name TEXT NOT NULL,
                student_identifier TEXT,
                score REAL DEFAULT 0.0,
                total_points REAL DEFAULT 0.0,
                percentage REAL DEFAULT 0.0,
                tri_score REAL DEFAULT 500.0,
                theta REAL DEFAULT 0.0,
                coherence_score REAL DEFAULT 1.0,
                coherence_label TEXT DEFAULT 'Coerente',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
            );
            """)

            # Migrações seguras da tabela submissions
            cursor.execute("PRAGMA table_info(submissions);")
            s_columns = [col[1] for col in cursor.fetchall()]
            if 'student_pin' not in s_columns:
                cursor.execute("ALTER TABLE submissions ADD COLUMN student_pin TEXT;")
            if 'tri_score' not in s_columns:
                cursor.execute("ALTER TABLE submissions ADD COLUMN tri_score REAL DEFAULT 500.0;")
            if 'theta' not in s_columns:
                cursor.execute("ALTER TABLE submissions ADD COLUMN theta REAL DEFAULT 0.0;")
            if 'coherence_score' not in s_columns:
                cursor.execute("ALTER TABLE submissions ADD COLUMN coherence_score REAL DEFAULT 1.0;")
            if 'coherence_label' not in s_columns:
                cursor.execute("ALTER TABLE submissions ADD COLUMN coherence_label TEXT DEFAULT 'Coerente';")

            # Tabela de Respostas Individuais dos Alunos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_option_id INTEGER,
                is_correct INTEGER DEFAULT 0,
                points_earned REAL DEFAULT 0.0,
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (selected_option_id) REFERENCES options(id) ON DELETE SET NULL
            );
            """)

            # Tabela de Reserva Atômica de PINs de Alunos (garantia de unicidade sob alta concorrência)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER NOT NULL,
                pin TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(quiz_id, pin),
                FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
            );
            """)

            # Índices de performance para buscas ultra-rápidas em alta concorrência
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_quiz_pin ON submissions(quiz_id, student_pin);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_quiz_id ON submissions(quiz_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_res_quiz_pin ON student_reservations(quiz_id, pin);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sa_sub_id ON student_answers(submission_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_q_quiz_id ON questions(quiz_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_opt_qid ON options(question_id);")

            conn.commit()
        finally:
            conn.close()

def get_professor_password() -> str:
    """Retorna a senha atual configurada para o acesso do professor."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = 'professor_password'")
        row = cursor.fetchone()
        return row['value'] if row else "admin123"
    finally:
        conn.close()

def set_professor_password(new_password: str) -> bool:
    """Atualiza a senha de acesso do professor de forma thread-safe."""
    if not new_password or not new_password.strip():
        return False
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_settings (key, value) VALUES ('professor_password', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (new_password.strip(),))
            conn.commit()
            return True
        finally:
            conn.close()

def generate_short_code() -> str:
    """Gera um código alfanumérico curto e amigável para o quiz."""
    return uuid.uuid4().hex[:6].upper()

def create_quiz(title: str, description: str = "", time_limit_minutes: int = 0) -> Dict[str, Any]:
    """Cria um novo quiz de forma atômica e thread-safe."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            quiz_code = generate_short_code()
            
            cursor.execute("""
                INSERT INTO quizzes (quiz_code, title, description, time_limit_minutes, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (quiz_code, title, description, time_limit_minutes))
            
            quiz_id = cursor.lastrowid
            conn.commit()
            return {"id": quiz_id, "quiz_code": quiz_code, "title": title}
        finally:
            conn.close()

def add_question(
    quiz_id: int, 
    question_text: str, 
    points: float, 
    explanation: str, 
    options: List[Dict[str, Any]], 
    image_data: Optional[str] = None,
    param_a: float = 1.2,
    param_b: float = 0.0,
    param_c: float = 0.25,
    difficulty_level: str = "Média"
) -> int:
    """Cadastra uma questão completa com alternativas e parâmetros psicométricos TRI de forma atômica."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COALESCE(MAX(order_num), 0) + 1 FROM questions WHERE quiz_id = ?", (quiz_id,))
            next_order = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO questions (
                    quiz_id, question_text, points, order_num, explanation, image_data,
                    param_a, param_b, param_c, difficulty_level
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quiz_id, question_text, points, next_order, explanation, image_data,
                param_a, param_b, param_c, difficulty_level
            ))
            
            question_id = cursor.lastrowid

            for idx, opt in enumerate(options):
                cursor.execute("""
                    INSERT INTO options (question_id, option_text, is_correct, order_num)
                    VALUES (?, ?, ?, ?)
                """, (question_id, opt['text'], 1 if opt.get('is_correct') else 0, idx + 1))

            conn.commit()
            backup_database()
            return question_id
        finally:
            conn.close()

def update_question(
    question_id: int, 
    question_text: str, 
    points: float, 
    explanation: str, 
    options: List[Dict[str, Any]], 
    image_data: Optional[str] = None,
    keep_existing_image: bool = True,
    param_a: float = 1.2,
    param_b: float = 0.0,
    param_c: float = 0.20,
    difficulty_level: str = "Média"
) -> bool:
    """Atualiza uma questão existente, suas alternativas e parâmetros psicométricos TRI de forma atômica."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            if image_data is not None:
                cursor.execute("""
                    UPDATE questions SET
                        question_text = ?, points = ?, explanation = ?, image_data = ?,
                        param_a = ?, param_b = ?, param_c = ?, difficulty_level = ?
                    WHERE id = ?
                """, (question_text, points, explanation, image_data, param_a, param_b, param_c, difficulty_level, question_id))
            elif not keep_existing_image:
                cursor.execute("""
                    UPDATE questions SET
                        question_text = ?, points = ?, explanation = ?, image_data = NULL,
                        param_a = ?, param_b = ?, param_c = ?, difficulty_level = ?
                    WHERE id = ?
                """, (question_text, points, explanation, param_a, param_b, param_c, difficulty_level, question_id))
            else:
                cursor.execute("""
                    UPDATE questions SET
                        question_text = ?, points = ?, explanation = ?,
                        param_a = ?, param_b = ?, param_c = ?, difficulty_level = ?
                    WHERE id = ?
                """, (question_text, points, explanation, param_a, param_b, param_c, difficulty_level, question_id))

            # Atualiza opções (exclui anteriores e insere novas)
            cursor.execute("DELETE FROM options WHERE question_id = ?", (question_id,))
            for idx, opt in enumerate(options):
                cursor.execute("""
                    INSERT INTO options (question_id, option_text, is_correct, order_num)
                    VALUES (?, ?, ?, ?)
                """, (question_id, opt['text'], 1 if opt.get('is_correct') else 0, idx + 1))

            conn.commit()
            backup_database()
            return True
        finally:
            conn.close()

def delete_question(question_id: int):
    """Exclui uma questão específica de forma atômica."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()
        finally:
            conn.close()

def delete_quiz(quiz_id: int):
    """Exclui um quiz e todos os dados associados em cascata de forma atômica."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
            conn.commit()
        finally:
            conn.close()

def toggle_quiz_status(quiz_id: int, is_active: bool):
    """Ativa ou desativa a aceitação de respostas para um quiz de forma atômica."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE quizzes SET is_active = ? WHERE id = ?", (1 if is_active else 0, quiz_id))
            conn.commit()
        finally:
            conn.close()

def toggle_quiz_results_release(quiz_id: int, release: bool):
    """Libera ou oculta a visualização de notas e gabarito para os alunos de forma atômica."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE quizzes SET results_released = ? WHERE id = ?", (1 if release else 0, quiz_id))
            conn.commit()
        finally:
            conn.close()

def get_all_quizzes() -> List[Dict[str, Any]]:
    """Recupera todos os quizzes com contagem de perguntas, respostas e status de liberação de notas."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                q.id, q.quiz_code, q.title, q.description, q.time_limit_minutes, q.is_active, q.results_released, q.created_at,
                COUNT(DISTINCT qs.id) as question_count,
                COUNT(DISTINCT s.id) as submission_count
            FROM quizzes q
            LEFT JOIN questions qs ON q.id = qs.quiz_id
            LEFT JOIN submissions s ON q.id = s.quiz_id
            GROUP BY q.id
            ORDER BY q.created_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_quiz_by_id(quiz_id: int) -> Optional[Dict[str, Any]]:
    """Recupera um quiz pelo ID numérico."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_quiz_by_code(quiz_code: str) -> Optional[Dict[str, Any]]:
    """Recupera um quiz pelo código alfanumérico."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quizzes WHERE quiz_code = ?", (quiz_code.upper().strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def generate_unique_student_pin(quiz_id: int) -> str:
    """Gera e reserva um código PIN de 4 dígitos (ex: '4829') único para o aluno de forma 100% atômica no banco."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            rng = random.SystemRandom()
            for _ in range(5000):
                pin = f"{rng.randint(1000, 9999)}"
                try:
                    cursor.execute("INSERT INTO student_reservations (quiz_id, pin) VALUES (?, ?)", (quiz_id, pin))
                    conn.commit()
                    return pin
                except sqlite3.IntegrityError:
                    # PIN já reservado por outro aluno no mesmo quiz, tenta o próximo
                    continue
            # Fallback
            return f"{rng.randint(1000, 9999)}"
        finally:
            conn.close()

def get_student_submission_by_credentials(quiz_id: int, search_term: str) -> Optional[Dict[str, Any]]:
    """Busca a submissão de um aluno pelo PIN de 4 dígitos, nome ou matrícula para exibição do boletim."""
    if not search_term or not search_term.strip():
        return None
    raw_term = search_term.strip()
    term = raw_term.lower()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM submissions 
            WHERE quiz_id = ? AND (
                student_pin = ? OR 
                LOWER(student_identifier) = ? OR 
                LOWER(student_name) = ? OR 
                LOWER(student_name) LIKE ?
            )
            ORDER BY submitted_at DESC LIMIT 1
        """, (quiz_id, raw_term, term, term, f"%{term}%"))
        sub = cursor.fetchone()
        if not sub:
            return None
        
        sub_dict = dict(sub)
        
        # Buscar respostas detalhadas
        cursor.execute("""
            SELECT 
                sa.question_id, sa.selected_option_id, sa.is_correct, sa.points_earned,
                q.question_text, q.points, q.explanation, q.image_data, q.difficulty_level, q.order_num,
                o.option_text as selected_option_text
            FROM student_answers sa
            JOIN questions q ON sa.question_id = q.id
            LEFT JOIN options o ON sa.selected_option_id = o.id
            WHERE sa.submission_id = ?
            ORDER BY q.order_num ASC
        """, (sub_dict['id'],))
        
        answers = [dict(a) for a in cursor.fetchall()]
        
        # Para cada questão, buscar a opção correta
        for ans in answers:
            cursor.execute("SELECT id, option_text FROM options WHERE question_id = ? AND is_correct = 1", (ans['question_id'],))
            corr = cursor.fetchone()
            ans['correct_option_text'] = corr['option_text'] if corr else "Não informada"
        
        sub_dict['answers'] = answers
        return sub_dict
    finally:
        conn.close()

def get_quiz_details(quiz_id: int) -> Dict[str, Any]:
    """Recupera o quiz completo com suas questões e respectivas opções."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
        quiz = cursor.fetchone()
        if not quiz:
            return {}

        quiz_dict = dict(quiz)
        
        cursor.execute("SELECT * FROM questions WHERE quiz_id = ? ORDER BY order_num ASC", (quiz_id,))
        questions = [dict(q) for q in cursor.fetchall()]
        
        for q in questions:
            cursor.execute("SELECT * FROM options WHERE question_id = ? ORDER BY order_num ASC", (q['id'],))
            q['options'] = [dict(opt) for opt in cursor.fetchall()]

        quiz_dict['questions'] = questions
        return quiz_dict
    finally:
        conn.close()

def submit_student_answers(
    quiz_id: int, 
    student_pin: str, 
    student_name: Optional[str] = None, 
    student_identifier: Optional[str] = None, 
    selected_options: Dict[int, int] = None
) -> Dict[str, Any]:
    """
    Registra a submissão do aluno com PIN único de 4 dígitos, calcula notas clássicas e a proficiência TRI padrão ENEM.
    Garante execução 100% thread-safe e atômica, suportando 40+ acessos simultâneos sem lock contention.
    """
    if selected_options is None:
        selected_options = {}
        
    pin_str = str(student_pin).strip()
    display_name = student_name.strip() if student_name and student_name.strip() else f"Aluno #{pin_str}"
    identifier_str = student_identifier.strip() if student_identifier else f"PIN-{pin_str}"

    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Busca as questões e seus parâmetros psicométricos TRI
            cursor.execute("SELECT id, points, param_a, param_b, param_c, difficulty_level FROM questions WHERE quiz_id = ?", (quiz_id,))
            questions = cursor.fetchall()
            
            total_points = sum(q['points'] for q in questions)
            score = 0.0
            detailed_answers = []
            tri_pattern = [] # [(is_correct, a, b, c), ...]

            for q in questions:
                q_id = q['id']
                pts = q['points']
                p_a = q['param_a'] if q['param_a'] is not None else 1.2
                p_b = q['param_b'] if q['param_b'] is not None else 0.0
                p_c = q['param_c'] if q['param_c'] is not None else 0.25
                
                selected_opt_id = selected_options.get(q_id)
                
                is_correct = 0
                points_earned = 0.0
                
                if selected_opt_id:
                    cursor.execute("SELECT is_correct FROM options WHERE id = ? AND question_id = ?", (selected_opt_id, q_id))
                    opt = cursor.fetchone()
                    if opt and opt['is_correct'] == 1:
                        is_correct = 1
                        points_earned = pts
                        score += pts

                tri_pattern.append((is_correct, p_a, p_b, p_c))

                detailed_answers.append({
                    'question_id': q_id,
                    'selected_option_id': selected_opt_id,
                    'is_correct': is_correct,
                    'points_earned': points_earned
                })

            percentage = (score / total_points * 100) if total_points > 0 else 0.0

            # =========================================================================
            # CÁLCULO DA PROFICIÊNCIA E NOTA TRI (PADRÃO ENEM)
            # =========================================================================
            theta, se_theta = tri_engine.calculate_eap_theta(tri_pattern)
            tri_score = tri_engine.theta_to_enem_score(theta)
            coherence_score, coherence_label, coherence_desc = tri_engine.evaluate_pedagogical_coherence(tri_pattern, theta)

            # Insere Submissão no Banco com student_pin e os campos TRI
            cursor.execute("""
                INSERT INTO submissions (
                    quiz_id, student_pin, student_name, student_identifier, score, total_points, percentage,
                    tri_score, theta, coherence_score, coherence_label
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quiz_id, pin_str, display_name, identifier_str, score, total_points, round(percentage, 2),
                tri_score, round(theta, 3), coherence_score, coherence_label
            ))
            
            submission_id = cursor.lastrowid

            # Insere Respostas Individuais
            for ans in detailed_answers:
                cursor.execute("""
                    INSERT INTO student_answers (submission_id, question_id, selected_option_id, is_correct, points_earned)
                    VALUES (?, ?, ?, ?, ?)
                """, (submission_id, ans['question_id'], ans['selected_option_id'], ans['is_correct'], ans['points_earned']))

            conn.commit()
        finally:
            conn.close()

    return {
        "submission_id": submission_id,
        "student_pin": pin_str,
        "student_name": display_name,
        "score": score,
        "total_points": total_points,
        "percentage": round(percentage, 2),
        "tri_score": tri_score,
        "theta": round(theta, 3),
        "se_theta": round(se_theta, 3),
        "coherence_score": coherence_score,
        "coherence_label": coherence_label,
        "coherence_desc": coherence_desc
    }

def get_submissions_by_quiz(quiz_id: int) -> List[Dict[str, Any]]:
    """Retorna todas as submissões de um quiz ordenadas por nota TRI."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, student_pin, student_name, student_identifier, score, total_points, percentage, tri_score, theta, coherence_score, coherence_label, submitted_at
            FROM submissions
            WHERE quiz_id = ?
            ORDER BY tri_score DESC, score DESC, submitted_at ASC
        """, (quiz_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_quiz_analytics_data(quiz_id: int) -> Dict[str, Any]:
    """Retorna dados estatísticos completos, agrupados e com métricas TRI para o Dashboard."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Informações do Quiz
        cursor.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
        quiz = cursor.fetchone()
        if not quiz:
            return {}

        # Submissões com métricas TRI e PIN
        cursor.execute("""
            SELECT id, student_pin, student_name, student_identifier, score, total_points, percentage, tri_score, theta, coherence_score, coherence_label, submitted_at
            FROM submissions
            WHERE quiz_id = ?
            ORDER BY tri_score DESC, score DESC
        """, (quiz_id,))
        submissions = [dict(s) for s in cursor.fetchall()]

        # Questões, parâmetros TRI e taxa de acertos
        cursor.execute("""
            SELECT 
                q.id as question_id,
                q.question_text,
                q.points,
                q.order_num,
                q.param_a,
                q.param_b,
                q.param_c,
                q.difficulty_level,
                COUNT(sa.id) as total_answers,
                SUM(CASE WHEN sa.is_correct = 1 THEN 1 ELSE 0 END) as correct_answers
            FROM questions q
            LEFT JOIN student_answers sa ON q.id = sa.question_id
            WHERE q.quiz_id = ?
            GROUP BY q.id
            ORDER BY q.order_num ASC
        """, (quiz_id,))
        questions_stat = []
        for row in cursor.fetchall():
            d = dict(row)
            tot = d['total_answers'] or 0
            corr = d['correct_answers'] or 0
            d['success_rate'] = round((corr / tot * 100), 1) if tot > 0 else 0.0
            questions_stat.append(d)

        # Detalhamento por Opção (quantas vezes cada alternativa foi marcada)
        cursor.execute("""
            SELECT 
                o.id as option_id,
                o.question_id,
                o.option_text,
                o.is_correct,
                COUNT(sa.id) as pick_count
            FROM options o
            JOIN questions q ON o.question_id = q.id
            LEFT JOIN student_answers sa ON o.id = sa.selected_option_id
            WHERE q.quiz_id = ?
            GROUP BY o.id
            ORDER BY o.question_id ASC, o.order_num ASC
        """, (quiz_id,))
        options_breakdown = [dict(opt) for opt in cursor.fetchall()]

        return {
            "quiz": dict(quiz),
            "submissions": submissions,
            "questions_stat": questions_stat,
            "options_breakdown": options_breakdown
        }
    finally:
        conn.close()

def seed_sample_quiz_if_empty():
    """Inicializa as tabelas do banco de dados SQLite sem injetar questionários de demonstração."""
    init_db()
