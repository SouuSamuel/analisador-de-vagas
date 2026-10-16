import requests
from bs4 import BeautifulSoup

from config import LIMITE_CARACTERES

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Sites que bloqueiam acesso automático ou exigem login
SITES_BLOQUEADOS = ("indeed.com", "linkedin.com", "glassdoor.com", "gupy.io", "infojobs.com.br")


def _mensagem_colar_manual(motivo: str) -> str:
    return (
        f"{motivo}\n\n"
        "Abra a vaga no navegador, copie a descrição e cole no campo "
        "'Descrição da vaga'."
    )


def extrair_texto_da_url(url: str) -> str:
    """Baixa a página da vaga e devolve só o texto visível."""
    if any(site in url.lower() for site in SITES_BLOQUEADOS):
        raise ValueError(
            _mensagem_colar_manual("Esse site bloqueia leitura automática de vagas.")
        )

    try:
        resposta = requests.get(url, headers=HEADERS, timeout=15)
        resposta.raise_for_status()
    except requests.exceptions.HTTPError as erro:
        codigo = erro.response.status_code if erro.response is not None else "?"
        raise ValueError(
            _mensagem_colar_manual(f"O site recusou o acesso (erro {codigo}).")
        )
    except requests.exceptions.RequestException:
        raise ValueError(
            _mensagem_colar_manual("Não consegui acessar o link (verifique a URL e a conexão).")
        )

    soup = BeautifulSoup(resposta.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    linhas = [linha.strip() for linha in soup.get_text("\n").splitlines()]
    texto = "\n".join(linha for linha in linhas if linha)

    # Páginas com login ou renderizadas por JavaScript costumam voltar quase vazias
    if len(texto) < 300:
        raise ValueError(
            _mensagem_colar_manual(
                "Pouco conteúdo extraído do link (a página pode exigir login ou usar JavaScript)."
            )
        )
    return texto[:LIMITE_CARACTERES]