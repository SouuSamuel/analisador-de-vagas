from tkinter import filedialog, messagebox

import customtkinter as ctk

import curriculos
from componentes import COR_RUIM, TEXTO, TEXTO_SUAVE
from extrator_curriculo import extrair_texto_curriculo

SUGESTOES = ["Back-end", "Front-end", "Full-stack", "Mobile"]


class TelaCurriculos(ctk.CTkFrame):
    """Uma aba por categoria, cada uma com o seu currículo base."""

    def __init__(self, master, ao_mudar):
        super().__init__(master, corner_radius=16)
        self.ao_mudar = ao_mudar  # avisa o app para atualizar o seletor de currículo
        self.abas = None
        self.vazio = None
        self._por_nome = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        topo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            topo, text="Currículos base", anchor="w", font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            topo,
            text=(
                "Crie categorias (Back-end, Front-end...) e associe um currículo a cada uma. "
                "Na hora de analisar, basta escolher a categoria."
            ),
            anchor="w", justify="left", wraplength=620, text_color=TEXTO_SUAVE,
        ).grid(row=1, column=0, sticky="w")

        botoes = ctk.CTkFrame(topo, fg_color="transparent")
        botoes.grid(row=0, column=1, rowspan=2, sticky="e")
        ctk.CTkButton(botoes, text="+ Nova categoria", command=self._nova).pack(side="left", padx=4)
        self.btn_renomear = ctk.CTkButton(
            botoes, text="Renomear", width=90, fg_color="transparent",
            border_width=1, text_color=TEXTO, command=self._renomear,
        )
        self.btn_renomear.pack(side="left", padx=4)
        self.btn_excluir = ctk.CTkButton(
            botoes, text="Excluir", width=80, fg_color="transparent",
            border_width=1, text_color=COR_RUIM, command=self._excluir,
        )
        self.btn_excluir.pack(side="left", padx=4)

        self.area = ctk.CTkFrame(self, fg_color="transparent")
        self.area.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)

        self.recarregar()

    # ----------------------------------------------------------------- montagem
    def recarregar(self, selecionar=None):
        for w in (self.abas, self.vazio):
            if w is not None:
                w.destroy()
        self.abas = None
        self.vazio = None

        cats = curriculos.listar()
        self._por_nome = {c["nome"]: c for c in cats}
        estado = "normal" if cats else "disabled"
        self.btn_renomear.configure(state=estado)
        self.btn_excluir.configure(state=estado)

        if not cats:
            self._montar_vazio()
            return

        self.abas = ctk.CTkTabview(self.area, corner_radius=12)
        self.abas.pack(fill="both", expand=True)
        for cat in cats:
            aba = self.abas.add(cat["nome"])
            self._montar_aba(aba, cat)
        if selecionar in self._por_nome:
            self.abas.set(selecionar)

    def _montar_vazio(self):
        self.vazio = ctk.CTkFrame(self.area, fg_color="transparent")
        self.vazio.pack(expand=True)
        ctk.CTkLabel(
            self.vazio, text="Nenhuma categoria ainda", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            self.vazio,
            text="Clique em '+ Nova categoria' ou comece por uma sugestão:",
            text_color=TEXTO_SUAVE,
        ).pack(pady=(0, 10))
        linha = ctk.CTkFrame(self.vazio, fg_color="transparent")
        linha.pack()
        for nome in SUGESTOES:
            ctk.CTkButton(
                linha, text=nome, width=110, command=lambda n=nome: self._criar(n)
            ).pack(side="left", padx=4)

    def _montar_aba(self, aba, cat):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(2, weight=1)
        caminho = curriculos.caminho_arquivo(cat["id"])

        ctk.CTkLabel(
            aba,
            text=f"Currículo base: {cat['original']}" if caminho
            else "Nenhum currículo definido para esta categoria",
            anchor="w", font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        barra = ctk.CTkFrame(aba, fg_color="transparent")
        barra.grid(row=1, column=0, sticky="w", padx=10)
        ctk.CTkButton(
            barra, text="Trocar currículo" if caminho else "Escolher currículo",
            command=lambda: self._escolher(cat),
        ).pack(side="left", padx=(0, 8))
        if caminho:
            ctk.CTkButton(
                barra, text="Remover arquivo", fg_color="transparent", border_width=1,
                text_color=TEXTO, command=lambda: self._remover(cat),
            ).pack(side="left")

        caixa = ctk.CTkTextbox(aba, wrap="word")
        caixa.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        if caminho:
            try:
                texto = extrair_texto_curriculo(str(caminho))
                resumo = texto[:4000] + ("…" if len(texto) > 4000 else "")
                caixa.insert(
                    "1.0",
                    "Texto que será enviado para a análise (confira se foi lido corretamente):\n\n"
                    + resumo,
                )
            except Exception as erro:
                caixa.insert("1.0", f"Não foi possível ler o arquivo: {erro}")
        else:
            caixa.insert("1.0", "Escolha um currículo em PDF, DOCX ou TXT para esta categoria.")
        caixa.configure(state="disabled")

    # ------------------------------------------------------------------- ações
    def _categoria_atual(self):
        if self.abas is None:
            return None
        return self._por_nome.get(self.abas.get())

    def _nova(self):
        nome = ctk.CTkInputDialog(
            text="Nome da categoria (ex.: Back-end):", title="Nova categoria"
        ).get_input()
        if nome is not None:
            self._criar(nome)

    def _criar(self, nome: str):
        try:
            cat = curriculos.criar(nome)
        except ValueError as erro:
            messagebox.showwarning("Atenção", str(erro))
            return
        self.recarregar(selecionar=cat["nome"])
        self.ao_mudar()

    def _renomear(self):
        cat = self._categoria_atual()
        if not cat:
            return
        novo = ctk.CTkInputDialog(
            text=f"Novo nome para '{cat['nome']}':", title="Renomear categoria"
        ).get_input()
        if novo is None:
            return
        try:
            curriculos.renomear(cat["id"], novo)
        except ValueError as erro:
            messagebox.showwarning("Atenção", str(erro))
            return
        self.recarregar(selecionar=novo.strip())
        self.ao_mudar()

    def _excluir(self):
        cat = self._categoria_atual()
        if not cat:
            return
        if messagebox.askyesno(
            "Excluir categoria",
            f"Excluir a categoria '{cat['nome']}' e o currículo base dela?\n"
            "(O arquivo original no seu computador não é apagado.)",
        ):
            curriculos.excluir(cat["id"])
            self.recarregar()
            self.ao_mudar()

    def _escolher(self, cat):
        caminho = filedialog.askopenfilename(
            filetypes=[("Currículos", "*.pdf *.docx *.txt"), ("Todos", "*.*")]
        )
        if not caminho:
            return
        try:
            curriculos.definir_arquivo(cat["id"], caminho)
        except (ValueError, OSError) as erro:
            messagebox.showerror("Não foi possível salvar", str(erro))
            return
        self.recarregar(selecionar=cat["nome"])
        self.ao_mudar()

    def _remover(self, cat):
        curriculos.remover_arquivo(cat["id"])
        self.recarregar(selecionar=cat["nome"])
        self.ao_mudar()