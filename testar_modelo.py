from dotenv import find_dotenv
from google import genai
from google.genai import errors

from config import API_KEY, MODELO, MODELOS_RESERVA

print("Arquivo .env usado:", find_dotenv() or "NENHUM ENCONTRADO")
print(f"MODELO:         {MODELO!r}")
print(f"MODELO_RESERVA: {MODELOS_RESERVA!r}\n")

if not API_KEY:
    raise SystemExit("GEMINI_API_KEY vazia. Confira o arquivo .env.")

client = genai.Client(api_key=API_KEY)

# Os do .env primeiro, depois alguns que sabemos que existem na sua lista
candidatos = list(
    dict.fromkeys(
        [MODELO, *MODELOS_RESERVA, "gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    )
)

for nome in candidatos:
    try:
        r = client.models.generate_content(model=nome, contents="Responda apenas: ok")
        print(f"[OK]       {nome} -> {(r.text or '').strip()[:30]!r}")
    except errors.APIError as e:
        print(f"[ERRO {e.code}] {nome} -> {str(e.message)[:120]}")
    except Exception as e:
        print(f"[ERRO]     {nome} -> {e}")