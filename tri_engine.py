import math
from typing import List, Dict, Any, Tuple

# Fator de escala padrão logístico-normal para aproximação com a ogiva normal
D_FACTOR = 1.7

def prob_3pl(theta: float, a: float, b: float, c: float, d_factor: float = D_FACTOR) -> float:
    """
    Calcula a probabilidade P(theta) de um estudante com proficiência theta
    acertar um item com parâmetros (a, b, c) usando o Modelo Logístico 3PL.
    
    P_i(theta) = c_i + (1 - c_i) / (1 + e^(-D * a_i * (theta - b_i)))
    """
    exponent = -d_factor * a * (theta - b)
    # Limitação para evitar overflow numérico
    if exponent > 40.0:
        logit = 0.0
    elif exponent < -40.0:
        logit = 1.0
    else:
        logit = 1.0 / (1.0 + math.exp(exponent))
    
    return c + (1.0 - c) * logit

def normal_pdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    """Função densidade de probabilidade normal padronizada."""
    coeff = 1.0 / (sigma * math.sqrt(2.0 * math.pi))
    return coeff * math.exp(-0.5 * ((x - mu) / sigma) ** 2)

def calculate_eap_theta(
    answers_pattern: List[Tuple[int, float, float, float]],
    grid_points: int = 61,
    min_theta: float = -4.0,
    max_theta: float = 4.0
) -> Tuple[float, float]:
    """
    Calcula a proficiência theta estimada do estudante usando o método EAP (Expected A Posteriori).
    
    answers_pattern: Lista de tuplas (acertou: 1 ou 0, a, b, c)
    Retorna: (theta_estimado, erro_padrao_estimado)
    """
    if not answers_pattern:
        return 0.0, 1.0

    step = (max_theta - min_theta) / (grid_points - 1)
    thetas = [min_theta + i * step for i in range(grid_points)]
    
    posteriors = []
    
    for th in thetas:
        prior = normal_pdf(th, 0.0, 1.0)
        log_l = 0.0
        
        for is_correct, a, b, c in answers_pattern:
            p = prob_3pl(th, a, b, c)
            # Evita log(0)
            p = max(min(p, 0.999999), 0.000001)
            if is_correct == 1:
                log_l += math.log(p)
            else:
                log_l += math.log(1.0 - p)
        
        likelihood = math.exp(log_l) if log_l > -100 else 0.0
        posterior = likelihood * prior
        posteriors.append(posterior)
    
    sum_posterior = sum(posteriors)
    if sum_posterior <= 0.0:
        # Fallback caso a verossimilhança seja extremamente pequena
        total_hits = sum(u for u, _, _, _ in answers_pattern)
        prop = total_hits / len(answers_pattern)
        fallback_th = (prop - 0.5) * 4.0
        return fallback_th, 0.5

    # EAP Theta = E[Theta | Respostas]
    eap_theta = sum(th * post for th, post in zip(thetas, posteriors)) / sum_posterior
    
    # Variância a Posteriori = E[Theta^2 | Respostas] - (E[Theta | Respostas])^2
    var_theta = sum((th ** 2) * post for th, post in zip(thetas, posteriors)) / sum_posterior - (eap_theta ** 2)
    se_theta = math.sqrt(max(var_theta, 0.001))
    
    return eap_theta, se_theta

def theta_to_enem_score(theta: float, min_score: float = 300.0, max_score: float = 950.0) -> float:
    """
    Converte o valor de proficiência theta (escala normal) para a escala ENEM (Média 500, Desvio 100).
    Aplica limites razoáveis de prova objetiva (300 a 950).
    """
    raw_score = 500.0 + (theta * 100.0)
    return round(max(min(raw_score, max_score), min_score), 1)

def evaluate_pedagogical_coherence(
    answers_pattern: List[Tuple[int, float, float, float]],
    theta: float
) -> Tuple[float, str, str]:
    """
    Analisa a coerência pedagógica das respostas do aluno comparando o padrão esperado vs observado.
    
    Retorna:
    - coherence_score: pontuação de 0.0 a 1.0
    - label: 'Alta Coerência', 'Coerente' ou 'Indício de Chute (Incoerente)'
    - explanation: Texto explicativo sobre o padrão identificado
    """
    if not answers_pattern:
        return 1.0, "Coerente", "Questionário sem questões."

    # Ordenar questões pela dificuldade b
    sorted_items = sorted(answers_pattern, key=lambda x: x[2]) # x[2] = b
    
    # Calcular inversões de Guttman (quando o aluno erra uma questão mais fácil que outra que ele acertou)
    inversions = 0
    total_pairs = 0
    
    n = len(sorted_items)
    for i in range(n):
        for j in range(i + 1, n):
            # sorted_items[i] é mais fácil que sorted_items[j] (b_i < b_j)
            diff_b = sorted_items[j][2] - sorted_items[i][2]
            if diff_b > 0.3: # diferença relevante de dificuldade
                total_pairs += 1
                u_easy = sorted_items[i][0]
                u_hard = sorted_items[j][0]
                # Inversão: errou a fácil (0) e acertou a difícil (1)
                if u_easy == 0 and u_hard == 1:
                    inversions += 1

    inversion_rate = (inversions / total_pairs) if total_pairs > 0 else 0.0
    coherence_score = max(0.0, 1.0 - (inversion_rate * 1.5))

    total_hits = sum(u for u, _, _, _ in answers_pattern)
    
    if total_hits == 0 or total_hits == len(answers_pattern):
        return 1.0, "Alta Coerência", "Padrão uniforme de respostas."

    if coherence_score >= 0.80:
        label = "Alta Coerência Pedagógica"
        explanation = "Padrão de acertos muito consistente: acertou as questões da base e errou itens além de sua proficiência atual."
    elif coherence_score >= 0.55:
        label = "Coerência Regular"
        explanation = "Padrão de respostas equilibrado com pequenas oscilações entre questões de nível similar."
    else:
        label = "Indício de Chute (Incoerente)"
        explanation = "Foram identificados acertos em questões difíceis com erros em questões fáceis, caracterizando prováveis acertos ao acaso."

    return round(coherence_score, 2), label, explanation

def get_icc_curve_points(a: float, b: float, c: float, n_points: int = 50) -> Dict[str, List[float]]:
    """Gera os pontos (theta, probabilidade) para desenhar a Curva Característica do Item (CCI)."""
    step = 8.0 / (n_points - 1)
    thetas = [-4.0 + i * step for i in range(n_points)]
    probs = [prob_3pl(th, a, b, c) for th in thetas]
    enem_thetas = [theta_to_enem_score(th) for th in thetas]
    return {
        "theta": thetas,
        "enem_scale": enem_thetas,
        "probability": probs
    }
