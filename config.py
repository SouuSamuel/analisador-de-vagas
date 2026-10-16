import json
import os

from dotenv import load_dotenv

from caminhos import PASTA_DADOS

ARQUIVO_CONFIG = PASTA_DADOS / "config.json"

# Limite de caracteres enviados ao modelo por documento (evita estourar contexto)
LIMITE_CARACTERES = 30000

PADRAO_MODELO = "gemini-3.5-flash"
PADRAO_RESERVA = ["gemini-3.5-flash-lite"]

try:
    load_dotenv(override=True)  # só ajuda no desenvolvimento; no .exe normalmente não há .env
except Exception:
    pass


def limpar(valor) -> str:
    """Remove espaços, aspas e o prefixo 'models/' que às vezes vem colado no nome."""
    return str(valor or "").strip().strip('"').strip("'").replace("models/", "").strip()


def _lista(texto) -> list:
    return [limpar(m) for m in str(texto or "").split(",") if limpar(m)]


def carregar() -> dict:
    """Lê a configuração. Ordem de prioridade: config.json (tela de Configurações),
    depois .env / variáveis de ambiente, depois os padrões."""
    cfg = {
        "api_key": "",
        "modelo": PADRAO_MODELO,
        "modelos_reserva": list(PADRAO_RESERVA),
    }

    if os.getenv("GEMINI_API_KEY"):
        cfg["api_key"] = limpar(os.getenv("GEMINI_API_KEY"))
    if os.getenv("MODELO"):
        cfg["modelo"] = limpar(os.getenv("MODELO"))
    if os.getenv("MODELO_RESERVA"):
        cfg["modelos_reserva"] = _lista(os.getenv("MODELO_RESERVA"))

    try:
        salvo = json.loads(ARQUIVO_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        salvo = {}

    for chave in ("api_key", "modelo"):
        if salvo.get(chave):
            cfg[chave] = limpar(salvo[chave])
    reservas = [limpar(m) for m in (salvo.get("modelos_reserva") or []) if limpar(m)]
    if reservas:
        cfg["modelos_reserva"] = reservas

    return cfg


def salvar(api_key: str, modelo: str, modelos_reserva: list):
    dados = {
        "api_key": limpar(api_key),
        "modelo": limpar(modelo),
        "modelos_reserva": [limpar(m) for m in modelos_reserva if limpar(m)],
    }
    ARQUIVO_CONFIG.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


# Compatibilidade com os scripts listar_modelos.py e testar_modelo.py
_cfg = carregar()
API_KEY = _cfg["api_key"]
MODELO = _cfg["modelo"]
MODELOS_RESERVA = _cfg["modelos_reserva"]