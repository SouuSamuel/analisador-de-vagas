import json
import re
import time

from google import genai
from google.genai import errors, types

import config

# Erros temporários: vale tentar de novo
CODIGOS_TEMPORARIOS = {429, 500, 503, 504}
TENTATIVAS_POR_MODELO = 3

PROMPT_SISTEMA = """Você é um recrutador técnico sênior e consultor de carreira.
Sua tarefa é comparar um currículo com uma vaga, medir a compatibilidade e dizer exatamente o que mudar.

Regras gerais:
- Nunca invente experiências, tecnologias, cursos ou resultados que não estejam no currículo.
- Sempre que citar algo do currículo ou da vaga, inclua o trecho que justifica.
- Se o candidato não possui um requisito, diga isso claramente; não maquie a lacuna.
- Responda em português do Brasil.
- Responda SOMENTE com um JSON válido, sem texto antes ou depois e sem blocos de markdown.

Regras de pontuação (todas as porcentagens são inteiros de 0 a 100):
- "compatibilidade_geral" pesa mais os requisitos obrigatórios, depois os desejáveis e a experiência.
- Escala: 90-100 atende quase tudo; 75-89 atende a maioria dos obrigatórios; 50-74 atende
  parte relevante; abaixo de 50 há muitas lacunas.
- Use exatamente estas 4 categorias, nesta ordem: "Habilidades técnicas", "Experiência",
  "Formação", "Diferenciais e soft skills".
- "compatibilidade_potencial" é uma estimativa CONSERVADORA de quanto a compatibilidade subiria
  se o candidato aplicasse as mudanças sugeridas sem inventar nada. Nunca menor que a geral.

Regras para "mudancas_necessarias":
- No máximo 8 mudanças, ordenadas da mais para a menos impactante.
- "prioridade" deve ser exatamente "alta", "media" ou "baixa".
- "trecho_atual": copie literalmente o trecho do currículo a ser alterado, ou deixe "" se a
  mudança for acrescentar algo novo.
- "sugestao": texto pronto para colar no currículo, usando apenas fatos que já estão nele.
  Se a sugestão depender de uma informação que só o candidato sabe, escreva essa parte entre
  colchetes, por exemplo [nº de usuários] e deixe claro em "impacto" que só deve ser incluída se for verdade."""

FORMATO_JSON = """{
  "resumo_vaga": "cargo, senioridade e foco em uma frase",
  "compatibilidade_geral": 0,
  "justificativa": "2 a 3 frases explicando a nota",
  "categorias": [
    {"nome": "Habilidades técnicas", "percentual": 0, "comentario": "string curta"}
  ],
  "requisitos_obrigatorios": [
    {"requisito": "string", "atendido": true, "evidencia": "trecho do currículo ou vazio"}
  ],
  "requisitos_desejaveis": [
    {"requisito": "string", "atendido": false, "evidencia": "trecho do currículo ou vazio"}
  ],
  "pontos_fortes": ["string"],
  "lacunas": [
    {"item": "string", "como_mitigar": "string"}
  ],
  "palavras_chave_ats": ["string"],
  "mudancas_necessarias": [
    {
      "prioridade": "alta",
      "secao": "ex.: Resumo, Experiência, Projetos, Habilidades",
      "problema": "o que está fraco ou faltando em relação à vaga",
      "trecho_atual": "trecho literal do currículo ou vazio",
      "sugestao": "texto pronto para colar",
      "impacto": "por que isso aumenta a compatibilidade"
    }
  ],
  "compatibilidade_potencial": 0
}"""


def _extrair_json(texto: str) -> dict:
    """Converte a resposta do modelo em dict, tolerando cercas de markdown."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    return json.loads(texto)


def _chamar_modelo(client, modelo: str, mensagem_usuario: str):
    return client.models.generate_content(
        model=modelo,
        contents=mensagem_usuario,
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_SISTEMA,
            response_mime_type="application/json",
            temperature=0.3,
            max_output_tokens=8192,
        ),
    )


def _erro_final(erro) -> RuntimeError:
    """Mensagem amigável quando todas as tentativas falharam."""
    if erro is None:
        return RuntimeError("Não foi possível obter resposta da API Gemini.")
    if erro.code == 429:
        return RuntimeError(
            "Limite de uso da API atingido (nível gratuito). Aguarde um pouco e tente de novo."
        )
    if erro.code in (500, 503, 504):
        return RuntimeError(
            "Os servidores do Gemini estão sobrecarregados no momento, mesmo após "
            "várias tentativas e modelos reserva. Tente novamente em alguns minutos."
        )
    if erro.code == 404:
        return RuntimeError(
            "Nenhum dos modelos configurados foi encontrado.\n\n"
            f"Resposta da API: {erro.message}\n\n"
            "Abra ⚙ Configurações, use 'Testar conexão' e ajuste os nomes dos modelos."
        )
    return RuntimeError(f"Erro da API Gemini ({erro.code}): {erro.message}")


def analisar(vaga: str, curriculo: str) -> dict:
    cfg = config.carregar()
    if not cfg["api_key"]:
        raise RuntimeError(
            "Chave da API não configurada. Abra ⚙ Configurações e cole a sua chave do Gemini."
        )

    client = genai.Client(api_key=cfg["api_key"])

    mensagem_usuario = (
        f"<vaga>\n{vaga}\n</vaga>\n\n"
        f"<curriculo>\n{curriculo}\n</curriculo>\n\n"
        f"Analise a compatibilidade do currículo com a vaga e responda neste formato JSON:\n{FORMATO_JSON}"
    )

    modelos = [cfg["modelo"]] + [m for m in cfg["modelos_reserva"] if m != cfg["modelo"]]
    resposta = None
    ultimo_erro = None

    for modelo in modelos:
        for tentativa in range(TENTATIVAS_POR_MODELO):
            try:
                resposta = _chamar_modelo(client, modelo, mensagem_usuario)
                break
            except errors.APIError as erro:
                ultimo_erro = erro
                if erro.code == 404:
                    break  # modelo inexistente: vai para o próximo da lista
                if erro.code in CODIGOS_TEMPORARIOS:
                    if tentativa < TENTATIVAS_POR_MODELO - 1:
                        time.sleep(2 ** (tentativa + 1))  # espera 2s, depois 4s
                    continue
                if erro.code in (400, 401, 403):
                    raise RuntimeError(
                        f"A API recusou a requisição (erro {erro.code}). "
                        "Verifique se a chave nas Configurações está correta."
                    )
                raise _erro_final(erro)
        if resposta is not None:
            break

    if resposta is None:
        raise _erro_final(ultimo_erro)

    texto = resposta.text or ""

    try:
        return _extrair_json(texto)
    except json.JSONDecodeError as erro:
        raise ValueError(f"O modelo não devolveu um JSON válido: {erro}\n\n{texto}")


# ---------------------------------------------------------------- utilitários
def _dict(item, chave: str) -> dict:
    """Se o modelo devolver uma string onde esperávamos um objeto, adapta."""
    return item if isinstance(item, dict) else {chave: str(item)}


def _verdadeiro(valor) -> bool:
    return valor is True or str(valor).strip().lower() in ("true", "sim", "1")


def calcular_cobertura(r: dict) -> tuple:
    """Quantos requisitos obrigatórios foram atendidos: (atendidos, total)."""
    itens = [_dict(i, "requisito") for i in (r.get("requisitos_obrigatorios") or [])]
    atendidos = sum(1 for i in itens if _verdadeiro(i.get("atendido")))
    return atendidos, len(itens)


def formatar_resultado(r: dict) -> str:
    """Transforma o JSON da análise em relatório em texto (aba Relatório, copiar e salvar)."""
    L = []
    L.append(f"VAGA: {r.get('resumo_vaga', '-')}")
    L.append(f"COMPATIBILIDADE GERAL: {r.get('compatibilidade_geral', '-')}%")
    if r.get("compatibilidade_potencial") not in (None, ""):
        L.append(f"POTENCIAL APÓS AJUSTES (estimativa): {r['compatibilidade_potencial']}%")
    ok, total = calcular_cobertura(r)
    if total:
        L.append(f"REQUISITOS OBRIGATÓRIOS ATENDIDOS: {ok}/{total}")
    L.append(f"{r.get('justificativa', '')}\n")

    L.append("=== COMPATIBILIDADE POR ÁREA ===")
    for c in r.get("categorias") or []:
        c = _dict(c, "nome")
        L.append(f"- {c.get('nome', '')}: {c.get('percentual', '-')}%  {c.get('comentario', '')}")

    for titulo, chave in [
        ("REQUISITOS OBRIGATÓRIOS", "requisitos_obrigatorios"),
        ("REQUISITOS DESEJÁVEIS", "requisitos_desejaveis"),
    ]:
        L.append(f"\n=== {titulo} ===")
        for item in r.get(chave) or []:
            item = _dict(item, "requisito")
            marca = "[OK]" if _verdadeiro(item.get("atendido")) else "[FALTA]"
            L.append(f"{marca} {item.get('requisito', '')}")
            if item.get("evidencia"):
                L.append(f"      Evidência: {item['evidencia']}")

    L.append("\n=== PONTOS FORTES ===")
    L.extend(f"- {p}" for p in r.get("pontos_fortes") or [])

    L.append("\n=== LACUNAS ===")
    for g in r.get("lacunas") or []:
        g = _dict(g, "item")
        L.append(f"- {g.get('item', '')}")
        L.append(f"      Como mitigar: {g.get('como_mitigar', '')}")

    L.append("\n=== PALAVRAS-CHAVE PARA O CURRÍCULO (ATS) ===")
    L.append(", ".join(str(p) for p in r.get("palavras_chave_ats") or []))

    L.append("\n=== MUDANÇAS NECESSÁRIAS ===")
    for i, m in enumerate(r.get("mudancas_necessarias") or [], 1):
        m = _dict(m, "problema")
        L.append(f"\n{i}. [{str(m.get('prioridade', '')).upper()}] {m.get('secao', '')}")
        L.append(f"   Problema: {m.get('problema', '')}")
        if m.get("trecho_atual"):
            L.append(f"   Antes:    {m['trecho_atual']}")
        L.append(f"   Depois:   {m.get('sugestao', '')}")
        if m.get("impacto"):
            L.append(f"   Impacto:  {m['impacto']}")

    return "\n".join(L)