import tkinter as tk

import customtkinter as ctk

COR_OK = "#2ea043"
COR_ALERTA = "#d29922"
COR_RUIM = "#da3633"
COR_INFO = "#1f6feb"

FUNDO_CARD = ("#ebebeb", "#2b2b2b")
FUNDO_CARD_2 = ("#dcdcdc", "#353535")
FUNDO_ANTES = ("#f6dede", "#3b2626")
FUNDO_DEPOIS = ("#d9efdd", "#21372a")
TEXTO = ("gray10", "gray90")
TEXTO_SUAVE = ("gray30", "gray70")

COR_PRIORIDADE = {"alta": COR_RUIM, "media": COR_ALERTA, "baixa": COR_INFO}
ROTULO_PRIORIDADE = {"alta": "ALTA", "media": "MÉDIA", "baixa": "BAIXA"}
ORDEM_PRIORIDADE = {"alta": 0, "media": 1, "baixa": 2}


# ---------------------------------------------------------------- utilitários
def converter_nota(valor) -> int:
    """Garante um inteiro entre 0 e 100, mesmo se o modelo devolver algo estranho."""
    try:
        return max(0, min(100, int(float(str(valor).replace("%", "")))))
    except (TypeError, ValueError):
        return 0


def cor_da_nota(nota: float) -> str:
    if nota >= 75:
        return COR_OK
    if nota >= 50:
        return COR_ALERTA
    return COR_RUIM


def rotulo_da_nota(nota: int) -> tuple:
    if nota >= 80:
        texto = "Alta compatibilidade"
    elif nota >= 65:
        texto = "Boa compatibilidade"
    elif nota >= 50:
        texto = "Compatibilidade média"
    else:
        texto = "Baixa compatibilidade"
    return texto, cor_da_nota(nota)


def normalizar_prioridade(valor) -> str:
    p = str(valor or "").strip().lower().replace("é", "e")
    if p.startswith("alt"):
        return "alta"
    if p.startswith("med"):
        return "media"
    return "baixa"


def ordenar_mudancas(lista) -> list:
    """Garante dicts e ordena por prioridade (alta primeiro), mantendo a ordem do modelo."""
    itens = [m if isinstance(m, dict) else {"problema": str(m)} for m in (lista or [])]
    return sorted(itens, key=lambda m: ORDEM_PRIORIDADE[normalizar_prioridade(m.get("prioridade"))])


# ------------------------------------------------------------------- medidor
class MedidorCircular(ctk.CTkFrame):
    """Anel de progresso animado com a porcentagem no centro."""

    def __init__(self, master, fundo, tamanho=160, espessura=14):
        super().__init__(master, fg_color=fundo)
        self._fundo = fundo
        self.tamanho = tamanho
        self.espessura = espessura
        self.valor = 0.0
        self._alvo = 0
        self._texto = "--"
        self._job = None

        self.canvas = tk.Canvas(self, width=tamanho, height=tamanho, highlightthickness=0, bd=0)
        self.canvas.pack()
        self._desenhar()

    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "canvas"):
            self._desenhar()

    def _desenhar(self):
        c = self.canvas
        c.delete("all")
        c.configure(bg=self._apply_appearance_mode(self._fundo))

        t, e = self.tamanho, self.espessura
        m = e / 2 + 2
        trilho = self._apply_appearance_mode(("#cfcfcf", "#454545"))
        c.create_oval(m, m, t - m, t - m, outline=trilho, width=e)

        if self.valor > 0:
            extensao = -min(359.9, 3.6 * self.valor)
            c.create_arc(
                m, m, t - m, t - m,
                start=90, extent=extensao, style="arc",
                outline=cor_da_nota(self._alvo), width=e,
            )

        cor_texto = self._apply_appearance_mode(TEXTO)
        cor_suave = self._apply_appearance_mode(TEXTO_SUAVE)
        c.create_text(
            t / 2, t / 2 - 8, text=self._texto, fill=cor_texto,
            font=("Segoe UI", int(t * 0.24), "bold"),
        )
        c.create_text(
            t / 2, t / 2 + t * 0.18, text="compatível", fill=cor_suave, font=("Segoe UI", 10)
        )

    def definir(self, valor, animar=True):
        self._alvo = converter_nota(valor)
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        if animar:
            self._passo()
        else:
            self.valor = float(self._alvo)
            self._texto = f"{self._alvo}%"
            self._desenhar()

    def _passo(self):
        dif = self._alvo - self.valor
        if abs(dif) < 0.6:
            self.valor = float(self._alvo)
            self._job = None
        else:
            self.valor += dif * 0.14
            self._job = self.after(16, self._passo)
        self._texto = f"{int(round(self.valor))}%"
        self._desenhar()

    def resetar(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.valor = 0.0
        self._alvo = 0
        self._texto = "--"
        self._desenhar()


# ------------------------------------------------------------ peças pequenas
class Estatistica(ctk.CTkFrame):
    """Mini cartão com um número e um título."""

    def __init__(self, master, titulo: str):
        super().__init__(master, corner_radius=10, fg_color=FUNDO_CARD_2)
        self.lbl_valor = ctk.CTkLabel(
            self, text="--", anchor="w", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.lbl_valor.pack(anchor="w", padx=12, pady=(8, 0))
        ctk.CTkLabel(
            self, text=titulo, anchor="w", text_color=TEXTO_SUAVE, font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=12, pady=(0, 8))

    def definir(self, valor: str, cor=None):
        self.lbl_valor.configure(text=valor, text_color=cor or TEXTO)


class BarraCategoria(ctk.CTkFrame):
    """Nome, porcentagem, barra colorida e comentário de uma área."""

    def __init__(self, master, nome, percentual, comentario=""):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        n = converter_nota(percentual)
        cor = cor_da_nota(n)
        negrito = ctk.CTkFont(size=13, weight="bold")

        ctk.CTkLabel(self, text=str(nome), anchor="w", font=negrito).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(self, text=f"{n}%", text_color=cor, font=negrito).grid(
            row=0, column=1, sticky="e"
        )
        barra = ctk.CTkProgressBar(self, height=8, progress_color=cor)
        barra.set(n / 100)
        barra.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 2))

        self.lbl_com = None
        if comentario:
            self.lbl_com = ctk.CTkLabel(
                self, text=str(comentario), anchor="w", justify="left",
                wraplength=480, text_color=TEXTO_SUAVE,
            )
            self.lbl_com.grid(row=2, column=0, columnspan=2, sticky="w")

    def definir_largura(self, largura: int):
        if self.lbl_com is not None:
            self.lbl_com.configure(wraplength=largura)


# ------------------------------------------------------------ cartão do topo
class CartaoCompatibilidade(ctk.CTkFrame):
    """Cartão do topo: medidor, veredito, resumo e três estatísticas."""

    def __init__(self, master):
        super().__init__(master, corner_radius=16, fg_color=FUNDO_CARD)
        self.grid_columnconfigure(1, weight=1)

        self.medidor = MedidorCircular(self, fundo=FUNDO_CARD)
        self.medidor.grid(row=0, column=0, padx=18, pady=18)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=14)
        info.grid_columnconfigure(0, weight=1)

        self.chip = ctk.CTkLabel(
            info, text="AGUARDANDO ANÁLISE", width=210, height=24, corner_radius=8,
            fg_color=COR_INFO, text_color="white", font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.chip.grid(row=0, column=0, sticky="w")

        self.lbl_titulo = ctk.CTkLabel(
            info, text="Nenhuma vaga analisada", anchor="w", justify="left",
            wraplength=480, font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.lbl_titulo.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.lbl_just = ctk.CTkLabel(
            info, text="Selecione o currículo, informe a vaga e clique em Analisar.",
            anchor="w", justify="left", wraplength=480, text_color=TEXTO_SUAVE,
        )
        self.lbl_just.grid(row=2, column=0, sticky="ew", pady=(2, 8))

        tiles = ctk.CTkFrame(info, fg_color="transparent")
        tiles.grid(row=3, column=0, sticky="ew")
        for col in range(3):
            tiles.grid_columnconfigure(col, weight=1)
        self.t_req = Estatistica(tiles, "Requisitos obrigatórios")
        self.t_mud = Estatistica(tiles, "Mudanças sugeridas")
        self.t_pot = Estatistica(tiles, "Potencial após ajustes")
        self.t_req.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.t_mud.grid(row=0, column=1, sticky="ew", padx=3)
        self.t_pot.grid(row=0, column=2, sticky="ew", padx=(6, 0))

    def definir_largura(self, largura: int):
        largura = max(250, largura)
        self.lbl_titulo.configure(wraplength=largura)
        self.lbl_just.configure(wraplength=largura)

    def atualizar(self, r: dict, cobertura: tuple, mudancas: list):
        n = converter_nota(r.get("compatibilidade_geral", r.get("nota_aderencia")))
        texto, cor = rotulo_da_nota(n)

        self.medidor.definir(n)
        self.chip.configure(text=texto.upper(), fg_color=cor)
        self.lbl_titulo.configure(text=str(r.get("resumo_vaga") or "Vaga analisada"))
        self.lbl_just.configure(
            text=str(r.get("justificativa") or r.get("justificativa_nota") or "")
        )

        ok, total = cobertura
        if total:
            self.t_req.definir(f"{ok}/{total}", cor_da_nota(ok / total * 100))
        else:
            self.t_req.definir("--")

        altas = sum(1 for m in mudancas if normalizar_prioridade(m.get("prioridade")) == "alta")
        self.t_mud.definir(f"{len(mudancas)} ({altas} altas)")

        pot = r.get("compatibilidade_potencial")
        if pot in (None, ""):
            self.t_pot.definir("--")
        else:
            self.t_pot.definir(f"~{max(converter_nota(pot), n)}%", COR_OK)

    def resetar(self):
        self.medidor.resetar()
        self.chip.configure(text="AGUARDANDO ANÁLISE", fg_color=COR_INFO)
        self.lbl_titulo.configure(text="Nenhuma vaga analisada")
        self.lbl_just.configure(text="Selecione o currículo, informe a vaga e clique em Analisar.")
        for tile in (self.t_req, self.t_mud, self.t_pot):
            tile.definir("--")


# -------------------------------------------------------------- lista de cards
class ListaCards(ctk.CTkScrollableFrame):
    """Lista rolável de cartões usada em cada aba do resultado."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._widgets = []
        self._rotulos = []  # (label, dedução) para reajustar a quebra de linha
        self._barras = []
        self._largura = 560
        self._linha = 0

    def _quebra(self, deducao: int) -> int:
        return max(180, self._largura - deducao)

    def definir_largura(self, largura: int):
        self._largura = largura
        for rotulo, deducao in self._rotulos:
            rotulo.configure(wraplength=self._quebra(deducao))
        for barra in self._barras:
            barra.definir_largura(self._quebra(60))

    def limpar(self):
        for w in self._widgets:
            w.destroy()
        self._widgets.clear()
        self._rotulos.clear()
        self._barras.clear()
        self._linha = 0

    def _registrar(self, widget):
        self._widgets.append(widget)
        self._linha += 1

    def _rotulo(self, pai, linha, texto, deducao, cor_texto=None, negrito=False,
                padx=(12, 12), pady=(6, 0)):
        lbl = ctk.CTkLabel(
            pai, text=str(texto), anchor="w", justify="left",
            wraplength=self._quebra(deducao), text_color=cor_texto or TEXTO,
            font=ctk.CTkFont(size=13, weight="bold") if negrito else None,
        )
        lbl.grid(row=linha, column=0, sticky="ew", padx=padx, pady=pady)
        self._rotulos.append((lbl, deducao))
        return lbl

    def adicionar_vazio(self, texto: str):
        lbl = ctk.CTkLabel(self, text=texto, text_color=TEXTO_SUAVE)
        lbl.grid(row=self._linha, column=0, pady=30)
        self._registrar(lbl)

    def adicionar_titulo(self, texto: str):
        lbl = ctk.CTkLabel(
            self, text=texto, anchor="w", font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl.grid(row=self._linha, column=0, sticky="w", padx=6, pady=(14, 2))
        self._registrar(lbl)

    def adicionar_categorias(self, categorias: list):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=FUNDO_CARD)
        card.grid(row=self._linha, column=0, sticky="ew", padx=4, pady=4)
        card.grid_columnconfigure(0, weight=1)
        for i, c in enumerate(categorias):
            barra = BarraCategoria(
                card, c.get("nome", ""), c.get("percentual"), c.get("comentario", "")
            )
            barra.grid(row=i, column=0, sticky="ew", padx=14, pady=8)
            barra.definir_largura(self._quebra(60))
            self._barras.append(barra)
        self._registrar(card)

    def adicionar_item(self, titulo, detalhe: str = "", tag: str = None, cor: str = COR_INFO):
        card = ctk.CTkFrame(self, corner_radius=10, fg_color=FUNDO_CARD)
        card.grid(row=self._linha, column=0, sticky="ew", padx=4, pady=4)
        card.grid_columnconfigure(1, weight=1)

        com_tag = bool(tag)
        deducao = 110 if com_tag else 40
        if com_tag:
            ctk.CTkLabel(
                card, text=tag, width=72, height=24, corner_radius=6,
                fg_color=cor, text_color="white", font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=10, sticky="n")

        lbl_titulo = ctk.CTkLabel(
            card, text=str(titulo), anchor="w", justify="left",
            wraplength=self._quebra(deducao), font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_titulo.grid(
            row=0, column=1, sticky="ew",
            padx=(0 if com_tag else 12, 12), pady=(10, 0 if detalhe else 10),
        )
        self._rotulos.append((lbl_titulo, deducao))

        if detalhe:
            lbl_det = ctk.CTkLabel(
                card, text=str(detalhe), anchor="w", justify="left",
                wraplength=self._quebra(deducao), text_color=TEXTO_SUAVE,
            )
            lbl_det.grid(
                row=1, column=1, sticky="ew",
                padx=(0 if com_tag else 12, 12), pady=(2, 10),
            )
            self._rotulos.append((lbl_det, deducao))

        self._registrar(card)

    def _caixa(self, card, linha, titulo, texto, fundo, cor_titulo):
        caixa = ctk.CTkFrame(card, corner_radius=8, fg_color=fundo)
        caixa.grid(row=linha, column=0, sticky="ew", padx=12, pady=(8, 0))
        caixa.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            caixa, text=titulo, anchor="w", text_color=cor_titulo,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
        self._rotulo(caixa, 1, texto, 80, padx=(10, 10), pady=(0, 8))

    def adicionar_mudanca(self, numero: int, m: dict, ao_copiar):
        prio = normalizar_prioridade(m.get("prioridade"))
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=FUNDO_CARD)
        card.grid(row=self._linha, column=0, sticky="ew", padx=4, pady=6)
        card.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        ctk.CTkLabel(
            topo, text=ROTULO_PRIORIDADE[prio], width=64, height=22, corner_radius=6,
            fg_color=COR_PRIORIDADE[prio], text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            topo, text=f"{numero}. {m.get('secao') or 'Currículo'}",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=10)

        linha = 1
        if m.get("problema"):
            self._rotulo(card, linha, m["problema"], 60, pady=(8, 0))
            linha += 1
        if m.get("trecho_atual"):
            self._caixa(card, linha, "ANTES", m["trecho_atual"], FUNDO_ANTES, COR_RUIM)
            linha += 1
        sugestao = m.get("sugestao")
        if sugestao:
            self._caixa(card, linha, "DEPOIS (SUGESTÃO)", sugestao, FUNDO_DEPOIS, COR_OK)
            linha += 1
        if m.get("impacto"):
            self._rotulo(card, linha, f"Impacto: {m['impacto']}", 60,
                         cor_texto=TEXTO_SUAVE, pady=(8, 0))
            linha += 1

        if sugestao:
            ctk.CTkButton(
                card, text="Copiar sugestão", width=130, height=28,
                command=lambda t=str(sugestao): ao_copiar(t),
            ).grid(row=linha, column=0, sticky="w", padx=12, pady=(8, 12))
        else:
            ctk.CTkFrame(card, height=8, fg_color="transparent").grid(row=linha, column=0)

        self._registrar(card)