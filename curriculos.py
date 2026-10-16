import json
import shutil
import uuid
from pathlib import Path

from caminhos import PASTA_CURRICULOS, PASTA_DADOS

ARQUIVO = PASTA_DADOS / "curriculos.json"
EXTENSOES = {".pdf", ".docx", ".txt"}


def _carregar() -> list:
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _salvar(lista: list):
    ARQUIVO.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def _validar_nome(nome: str, ignorar_id=None) -> str:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe um nome para a categoria.")
    if len(nome) > 30:
        raise ValueError("Use no máximo 30 caracteres no nome da categoria.")
    for c in _carregar():
        if c["id"] != ignorar_id and c["nome"].lower() == nome.lower():
            raise ValueError(f"Já existe uma categoria chamada '{c['nome']}'.")
    return nome


def _apagar_arquivo(cat: dict):
    if cat.get("arquivo"):
        (PASTA_CURRICULOS / cat["arquivo"]).unlink(missing_ok=True)


def listar() -> list:
    return _carregar()


def obter(id_categoria: str):
    return next((c for c in _carregar() if c["id"] == id_categoria), None)


def criar(nome: str) -> dict:
    nome = _validar_nome(nome)
    cat = {"id": uuid.uuid4().hex[:8], "nome": nome, "arquivo": "", "original": ""}
    lista = _carregar()
    lista.append(cat)
    _salvar(lista)
    return cat


def renomear(id_categoria: str, novo_nome: str):
    novo_nome = _validar_nome(novo_nome, ignorar_id=id_categoria)
    lista = _carregar()
    for c in lista:
        if c["id"] == id_categoria:
            c["nome"] = novo_nome
    _salvar(lista)


def excluir(id_categoria: str):
    lista = _carregar()
    for c in lista:
        if c["id"] == id_categoria:
            _apagar_arquivo(c)
    _salvar([c for c in lista if c["id"] != id_categoria])


def definir_arquivo(id_categoria: str, caminho_origem: str):
    """Copia o currículo para a pasta do app e associa à categoria."""
    origem = Path(caminho_origem)
    if origem.suffix.lower() not in EXTENSOES:
        raise ValueError("Formato não suportado. Use PDF, DOCX ou TXT.")

    lista = _carregar()
    cat = next((c for c in lista if c["id"] == id_categoria), None)
    if cat is None:
        raise ValueError("Categoria não encontrada.")

    destino = PASTA_CURRICULOS / f"{cat['id']}_{uuid.uuid4().hex[:6]}{origem.suffix.lower()}"
    shutil.copy2(origem, destino)
    _apagar_arquivo(cat)  # remove a versão anterior
    cat["arquivo"] = destino.name
    cat["original"] = origem.name
    _salvar(lista)


def remover_arquivo(id_categoria: str):
    lista = _carregar()
    for c in lista:
        if c["id"] == id_categoria:
            _apagar_arquivo(c)
            c["arquivo"] = ""
            c["original"] = ""
    _salvar(lista)


def caminho_arquivo(id_categoria: str):
    """Caminho do currículo da categoria, ou None se não houver arquivo."""
    cat = obter(id_categoria)
    if cat and cat.get("arquivo"):
        caminho = PASTA_CURRICULOS / cat["arquivo"]
        return caminho if caminho.exists() else None
    return None