from google import genai

from config import API_KEY, MODELO, MODELOS_RESERVA

if not API_KEY:
    raise SystemExit("GEMINI_API_KEY não encontrada. Confira o arquivo .env.")

client = genai.Client(api_key=API_KEY)

print(f"MODELO lido do .env:         {MODELO!r}")
print(f"MODELO_RESERVA lido do .env: {MODELOS_RESERVA!r}\n")
print("Modelos disponíveis para a sua chave (generateContent):\n")

for m in client.models.list():
    acoes = getattr(m, "supported_actions", None) or []
    if "generateContent" in acoes:
        print(" ", m.name.replace("models/", ""))