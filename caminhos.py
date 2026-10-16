import os
from pathlib import Path

NOME_APP = "AnalisadorVagas"


def _pasta_base() -> Path:
    base = os.getenv("APPDATA")  # Windows: C:\Users\voce\AppData\Roaming
    if base:
        return Path(base) / NOME_APP
    return Path.home() / f".{NOME_APP.lower()}"


PASTA_DADOS = _pasta_base()
PASTA_CURRICULOS = PASTA_DADOS / "curriculos"

for _pasta in (PASTA_DADOS, PASTA_CURRICULOS):
    _pasta.mkdir(parents=True, exist_ok=True)