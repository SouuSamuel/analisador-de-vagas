from pathlib import Path

import pdfplumber
from docx import Document

from config import LIMITE_CARACTERES


def extrair_texto_curriculo(caminho: str) -> str:
    """Lê um currículo em PDF, DOCX ou TXT e devolve o texto puro."""
    arquivo = Path(caminho)
    extensao = arquivo.suffix.lower()

    if extensao == ".pdf":
        with pdfplumber.open(arquivo) as pdf:
            paginas = [pagina.extract_text() or "" for pagina in pdf.pages]
        texto = "\n".join(paginas)
    elif extensao == ".docx":
        doc = Document(arquivo)
        texto = "\n".join(p.text for p in doc.paragraphs)
    elif extensao == ".txt":
        texto = arquivo.read_text(encoding="utf-8")
    else:
        raise ValueError("Formato não suportado. Use PDF, DOCX ou TXT.")

    texto = texto.strip()
    if not texto:
        raise ValueError(
            "Não consegui extrair texto do arquivo. "
            "Se for um PDF escaneado (imagem), exporte novamente com texto selecionável."
        )
    return texto[:LIMITE_CARACTERES]