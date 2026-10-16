import json
import os
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

# Em .exe sem console (--windowed) stdout/stderr podem ser None: evita travar bibliotecas
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import customtkinter as ctk

import curriculos
from analisador import analisar, calcular_cobertura, formatar_resultado
from caminhos import PASTA_DADOS
from componentes import (
    COR_ALERTA,
    COR_OK,
    COR_PRIORIDADE,
    COR_RUIM,
    ROTULO_PRIORIDADE,
    TEXTO,
    TEXTO_SUAVE,
    CartaoCompatibilidade,
    ListaCards,
    normalizar_prioridade,
    ordenar_mudancas,
)
from extrator_curriculo import extrair_texto_curriculo
from extrator_vaga import extrair_texto_da_url
from tela_config import TelaConfig
from tela_curriculos import TelaCurriculos

ctk.set_default_color_theme("blue")

ARQUIVO_PREFS = PASTA_DADOS / "preferencias.json"
ARQUIVO_ERROS = PASTA_DADOS / "erro.log"
ABAS = ["Resumo", "Mudanças", "Requisitos", "Pontos e lacunas", "Palavras-chave"]

OUTRO_ARQUIVO = "Outro arquivo…"
SEM_CURRICULO = "Selecione o currículo"
DICA_CURRICULO = "Cadastre currículos base na tela 'Currículos base' ou escolha um arquivo."


def carregar_prefs() -> dict:
    try:
        return json.loads(ARQUIVO_PREFS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def salvar_prefs(prefs: dict):
    try:
        ARQUIVO_PREFS.write_text(json.dumps(prefs, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def como_dict(item, chave: str) -> dict:
    """Se o modelo devolver uma string onde esperávamos um objeto, adapta."""
    return item if isinstance(item, dict) else {chave: str(item)}


def eh_verdadeiro(valor) -> bool:
    return valor is True or str(valor).strip().lower() in ("true", "sim", "1")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.prefs = carregar_prefs()
        ctk.set_appearance_mode(self.prefs.get("tema", "dark"))

        self.title("Analisador de Vagas")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.report_callback_exception = self._registrar_erro

        self.caminho_curriculo = None
        self.id_categoria_atual = None
        self._opcao_anterior = SEM_CURRICULO
        self._cats = {}
        self.ultimo_texto = ""
        self._job_resize = None
        self.listas = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._criar_cabecalho()

        self.tela_analise = ctk.CTkFrame(self, fg_color="transparent")
        self.tela_analise.grid(row=1, column=0, sticky="nsew")
        self.tela_analise.grid_columnconfigure(1, weight=1)
        self.tela_analise.grid_rowconfigure(0, weight=1)

        self.tela_curriculos = TelaCurriculos(self, ao_mudar=self._ao_mudar_curriculos)
        self.tela_curriculos.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.tela_curriculos.grid_remove()

        self._criar_painel_entrada()
        self._criar_painel_resultado()
        self._restaurar_curriculo()

        self.bind("<Configure>", self._ao_redimensionar)

    # --------------------------------------------------------- erros inesperados
    def _registrar_erro(self, exc, val, tb):
        texto = "".join(traceback.format_exception(exc, val, tb))
        try:
            with ARQUIVO_ERROS.open("a", encoding="utf-8") as f:
                f.write(texto + "\n")
        except OSError:
            pass
        messagebox.showerror(
            "Erro inesperado", f"{val}\n\nOs detalhes foram salvos em:\n{ARQUIVO_ERROS}"
        )

    # ------------------------------------------------------------------ layout
    def _criar_cabecalho(self):
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        cab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cab, text="Analisador de Vagas", font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            cab,
            text="Descubra sua compatibilidade com a vaga e o que mudar no currículo",
            text_color=TEXTO_SUAVE,
        ).grid(row=1, column=0, sticky="w")

        self.nav = ctk.CTkSegmentedButton(
            cab, values=["Analisar", "Currículos base"], command=self._trocar_tela
        )
        self.nav.set("Analisar")
        self.nav.grid(row=0, column=1, rowspan=2, padx=10)

        ctk.CTkButton(
            cab, text="⚙ Configurações", width=140, fg_color="transparent",
            border_width=1, text_color=TEXTO, command=self.abrir_config,
        ).grid(row=0, column=2, rowspan=2, padx=10)

        self.switch_tema = ctk.CTkSwitch(cab, text="Modo escuro", command=self._alternar_tema)
        if ctk.get_appearance_mode() == "Dark":
            self.switch_tema.select()
        self.switch_tema.grid(row=0, column=3, rowspan=2, sticky="e")

    def _criar_painel_entrada(self):
        p = ctk.CTkFrame(self.tela_analise, width=370, corner_radius=16)
        p.grid(row=0, column=0, sticky="ns", padx=(20, 10), pady=(10, 20))
        p.grid_propagate(False)
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(4, weight=1)

        negrito = ctk.CTkFont(size=14, weight="bold")

        # 1. Currículo
        ctk.CTkLabel(p, text="1. Currículo", font=negrito, anchor="w").grid(
            row=0, column=0, sticky="w", padx=15, pady=(15, 5)
        )
        quadro_cv = ctk.CTkFrame(p, fg_color="transparent")
        quadro_cv.grid(row=1, column=0, sticky="ew", padx=15)
        quadro_cv.grid_columnconfigure(0, weight=1)
        self.opcao_cv = ctk.CTkOptionMenu(
            quadro_cv, values=[OUTRO_ARQUIVO], command=self._ao_escolher_curriculo,
            dynamic_resizing=False,
        )
        self.opcao_cv.set(SEM_CURRICULO)
        self.opcao_cv.grid(row=0, column=0, sticky="ew")
        self.lbl_cv = ctk.CTkLabel(
            quadro_cv, text=DICA_CURRICULO, anchor="w", wraplength=320,
            justify="left", text_color=TEXTO_SUAVE,
        )
        self.lbl_cv.grid(row=1, column=0, sticky="w", pady=(6, 0))

        # 2. Vaga
        ctk.CTkLabel(p, text="2. Vaga", font=negrito, anchor="w").grid(
            row=2, column=0, sticky="w", padx=15, pady=(20, 5)
        )
        self.seg_modo = ctk.CTkSegmentedButton(
            p, values=["Colar descrição", "Link"], command=self._trocar_modo
        )
        self.seg_modo.set("Colar descrição")
        self.seg_modo.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 8))

        self.area_vaga = ctk.CTkFrame(p, fg_color="transparent")
        self.area_vaga.grid(row=4, column=0, sticky="nsew", padx=15, pady=(0, 10))
        self.area_vaga.grid_columnconfigure(0, weight=1)
        self.area_vaga.grid_rowconfigure(0, weight=1)

        self.txt_vaga = ctk.CTkTextbox(self.area_vaga, wrap="word")
        self.txt_vaga.grid(row=0, column=0, sticky="nsew")

        self.quadro_link = ctk.CTkFrame(self.area_vaga, fg_color="transparent")
        self.entry_url = ctk.CTkEntry(self.quadro_link, placeholder_text="https://...")
        self.entry_url.pack(fill="x")
        ctk.CTkLabel(
            self.quadro_link,
            text=(
                "Atenção: Indeed, LinkedIn, Gupy e outros sites grandes bloqueiam "
                "leitura automática. Nesses casos, use 'Colar descrição'."
            ),
            wraplength=320, justify="left", text_color=TEXTO_SUAVE,
        ).pack(anchor="w", pady=10)

        # Ações
        self.btn_analisar = ctk.CTkButton(
            p, text="Analisar", height=44, corner_radius=10,
            font=ctk.CTkFont(size=15, weight="bold"), command=self.iniciar_analise,
        )
        self.btn_analisar.grid(row=5, column=0, sticky="ew", padx=15, pady=(0, 6))

        self.btn_limpar = ctk.CTkButton(
            p, text="Limpar", fg_color="transparent", border_width=1,
            text_color=TEXTO, command=self.limpar,
        )
        self.btn_limpar.grid(row=6, column=0, sticky="ew", padx=15, pady=(0, 10))

        self.progresso = ctk.CTkProgressBar(p, mode="indeterminate")
        self.progresso.grid(row=7, column=0, sticky="ew", padx=15)
        self.progresso.grid_remove()

        self.lbl_status = ctk.CTkLabel(p, text="", wraplength=320, justify="left", anchor="w")
        self.lbl_status.grid(row=8, column=0, sticky="ew", padx=15, pady=(6, 15))

    def _criar_painel_resultado(self):
        self.painel_resultado = ctk.CTkFrame(self.tela_analise, fg_color="transparent")
        self.painel_resultado.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=(10, 20))
        self.painel_resultado.grid_columnconfigure(0, weight=1)
        self.painel_resultado.grid_rowconfigure(1, weight=1)

        self.cartao = CartaoCompatibilidade(self.painel_resultado)
        self.cartao.grid(row=0, column=0, sticky="ew")

        self.abas = ctk.CTkTabview(self.painel_resultado, corner_radius=12)
        self.abas.grid(row=1, column=0, sticky="nsew", pady=10)

        for nome in ABAS:
            aba = self.abas.add(nome)
            lista = ListaCards(aba)
            lista.pack(fill="both", expand=True)
            self.listas[nome] = lista

        aba_texto = self.abas.add("Relatório")
        self.txt_completo = ctk.CTkTextbox(aba_texto, wrap="word")
        self.txt_completo.pack(fill="both", expand=True)
        self.txt_completo.configure(state="disabled")

        barra = ctk.CTkFrame(self.painel_resultado, fg_color="transparent")
        barra.grid(row=2, column=0, sticky="e")
        self.btn_copiar = ctk.CTkButton(
            barra, text="Copiar relatório", width=140, command=self.copiar, state="disabled"
        )
        self.btn_copiar.pack(side="left", padx=(0, 8))
        self.btn_salvar = ctk.CTkButton(
            barra, text="Salvar relatório", width=140, command=self.salvar, state="disabled"
        )
        self.btn_salvar.pack(side="left")

        self._resetar_resultado()

    # ------------------------------------------------------------ navegação
    def _trocar_tela(self, valor: str):
        if valor == "Currículos base":
            self.tela_analise.grid_remove()
            self.tela_curriculos.grid()
        else:
            self.tela_curriculos.grid_remove()
            self.tela_analise.grid()
            self.after(50, self._ajustar_textos)

    def abrir_config(self):
        TelaConfig(self)

    def _alternar_tema(self):
        modo = "dark" if self.switch_tema.get() else "light"
        ctk.set_appearance_mode(modo)
        self.prefs["tema"] = modo
        salvar_prefs(self.prefs)

    def _trocar_modo(self, valor: str):
        if valor == "Link":
            self.txt_vaga.grid_remove()
            self.quadro_link.grid(row=0, column=0, sticky="new")
        else:
            self.quadro_link.grid_remove()
            self.txt_vaga.grid(row=0, column=0, sticky="nsew")

    # -------------------------------------------------------------- currículo
    def _atualizar_opcoes(self):
        self._cats = {
            c["nome"]: c for c in curriculos.listar() if curriculos.caminho_arquivo(c["id"])
        }
        self.opcao_cv.configure(values=[*self._cats, OUTRO_ARQUIVO])

    def _definir_curriculo(self, caminho, rotulo_opcao, descricao, id_categoria=None):
        self.caminho_curriculo = str(caminho)
        self.id_categoria_atual = id_categoria
        self._opcao_anterior = rotulo_opcao
        self.opcao_cv.set(rotulo_opcao)
        self.lbl_cv.configure(text=descricao, text_color=TEXTO)

    def _limpar_curriculo(self):
        self.caminho_curriculo = None
        self.id_categoria_atual = None
        self._opcao_anterior = SEM_CURRICULO
        self.opcao_cv.set(SEM_CURRICULO)
        self.lbl_cv.configure(text=DICA_CURRICULO, text_color=TEXTO_SUAVE)

    def _ao_escolher_curriculo(self, valor: str):
        if valor == OUTRO_ARQUIVO:
            caminho = filedialog.askopenfilename(
                filetypes=[("Currículos", "*.pdf *.docx *.txt"), ("Todos", "*.*")]
            )
            if not caminho:
                self.opcao_cv.set(self._opcao_anterior)
                return
            self._definir_curriculo(caminho, OUTRO_ARQUIVO, Path(caminho).name)
            self.prefs.update({"curriculo_origem": "arquivo", "curriculo": caminho})
        else:
            cat = self._cats.get(valor)
            caminho = curriculos.caminho_arquivo(cat["id"]) if cat else None
            if not caminho:
                self._limpar_curriculo()
                return
            self._definir_curriculo(
                caminho, cat["nome"], f"Currículo base: {cat['original']}", cat["id"]
            )
            self.prefs.update({"curriculo_origem": "categoria", "curriculo_categoria": cat["id"]})
        salvar_prefs(self.prefs)

    def _restaurar_curriculo(self):
        self._atualizar_opcoes()
        if self.prefs.get("curriculo_origem") == "categoria":
            cat = curriculos.obter(self.prefs.get("curriculo_categoria", ""))
            caminho = curriculos.caminho_arquivo(cat["id"]) if cat else None
            if caminho:
                self._definir_curriculo(
                    caminho, cat["nome"], f"Currículo base: {cat['original']}", cat["id"]
                )
            return
        ultimo = self.prefs.get("curriculo")
        if ultimo and Path(ultimo).exists():
            self._definir_curriculo(ultimo, OUTRO_ARQUIVO, Path(ultimo).name)

    def _ao_mudar_curriculos(self):
        """Chamado pela tela de currículos base após criar, trocar ou excluir algo."""
        self._atualizar_opcoes()
        if self.id_categoria_atual:
            cat = curriculos.obter(self.id_categoria_atual)
            caminho = curriculos.caminho_arquivo(cat["id"]) if cat else None
            if caminho:
                self._definir_curriculo(
                    caminho, cat["nome"], f"Currículo base: {cat['original']}", cat["id"]
                )
            else:
                self._limpar_curriculo()

    def limpar(self):
        self.txt_vaga.delete("1.0", "end")
        self.entry_url.delete(0, "end")
        self._resetar_resultado()
        self._status("")

    def _status(self, texto: str, cor=TEXTO_SUAVE):
        self.lbl_status.configure(text=texto, text_color=cor)

    # --------------------------------------------------------------- análise
    def iniciar_analise(self):
        if not self.caminho_curriculo:
            messagebox.showwarning("Atenção", "Selecione um currículo (base ou arquivo) primeiro.")
            return

        if self.seg_modo.get() == "Link":
            url = self.entry_url.get().strip()
            descricao = ""
            if not url:
                messagebox.showwarning("Atenção", "Informe o link da vaga.")
                return
        else:
            url = ""
            descricao = self.txt_vaga.get("1.0", "end").strip()
            if not descricao:
                messagebox.showwarning("Atenção", "Cole a descrição da vaga.")
                return

        self._definir_ocupado(True)
        threading.Thread(target=self._executar_analise, args=(url, descricao), daemon=True).start()

    def _executar_analise(self, url: str, descricao: str):
        """Roda em outra thread para não travar a janela."""
        try:
            curriculo = extrair_texto_curriculo(self.caminho_curriculo)
            vaga = extrair_texto_da_url(url) if url else descricao
            resultado = analisar(vaga, curriculo)
        except Exception as erro:
            self.after(0, self._falhou, str(erro))
            return
        self.after(0, self._concluir, resultado)

    def _definir_ocupado(self, ocupado: bool):
        if ocupado:
            self.btn_analisar.configure(state="disabled", text="Analisando...")
            self.progresso.grid()
            self.progresso.start()
            self._status("Lendo o currículo e analisando a vaga...")
        else:
            self.progresso.stop()
            self.progresso.grid_remove()
            self.btn_analisar.configure(state="normal", text="Analisar")

    def _falhou(self, mensagem: str):
        self._definir_ocupado(False)
        self._status("Falha na análise.", COR_RUIM)
        messagebox.showerror("Não foi possível analisar", mensagem)

    def _concluir(self, resultado: dict):
        self._definir_ocupado(False)
        try:
            self.mostrar_resultado(resultado)
            self._status("Análise concluída.", COR_OK)
        except Exception as erro:
            self._status("Resposta em formato inesperado.", COR_RUIM)
            messagebox.showerror("Erro ao exibir o resultado", str(erro))

    # ------------------------------------------------------------- resultado
    def _resetar_resultado(self):
        self.cartao.resetar()
        for lista in self.listas.values():
            lista.limpar()
            lista.adicionar_vazio("Nenhuma análise ainda.")
        self.txt_completo.configure(state="normal")
        self.txt_completo.delete("1.0", "end")
        self.txt_completo.configure(state="disabled")
        self.ultimo_texto = ""
        self.btn_copiar.configure(state="disabled")
        self.btn_salvar.configure(state="disabled")

    def mostrar_resultado(self, r: dict):
        for lista in self.listas.values():
            lista.limpar()

        cobertura = calcular_cobertura(r)
        mudancas = ordenar_mudancas(r.get("mudancas_necessarias"))
        self.cartao.atualizar(r, cobertura, mudancas)

        # ---- Resumo
        lista = self.listas["Resumo"]
        categorias = [como_dict(c, "nome") for c in (r.get("categorias") or [])]
        if categorias:
            lista.adicionar_titulo("Compatibilidade por área")
            lista.adicionar_categorias(categorias)
        principais = [
            m for m in mudancas if normalizar_prioridade(m.get("prioridade")) == "alta"
        ][:3] or mudancas[:3]
        if principais:
            lista.adicionar_titulo("O que mudar primeiro")
            for m in principais:
                prio = normalizar_prioridade(m.get("prioridade"))
                lista.adicionar_item(
                    m.get("secao") or "Currículo",
                    m.get("problema", ""),
                    tag=ROTULO_PRIORIDADE[prio],
                    cor=COR_PRIORIDADE[prio],
                )
        if not categorias and not principais:
            lista.adicionar_vazio("Sem dados de resumo.")

        # ---- Mudanças
        lista = self.listas["Mudanças"]
        if mudancas:
            lista.adicionar_titulo(
                f"{len(mudancas)} mudanças sugeridas (comece pelas de prioridade alta)"
            )
            for i, m in enumerate(mudancas, 1):
                lista.adicionar_mudanca(i, m, self.copiar_texto)
        else:
            lista.adicionar_vazio("Nenhuma mudança sugerida.")

        # ---- Requisitos
        lista = self.listas["Requisitos"]
        for titulo, chave in [
            ("Obrigatórios", "requisitos_obrigatorios"),
            ("Desejáveis", "requisitos_desejaveis"),
        ]:
            lista.adicionar_titulo(titulo)
            itens = r.get(chave) or []
            if not itens:
                lista.adicionar_item("Nenhum requisito identificado.")
            for item in itens:
                item = como_dict(item, "requisito")
                ok = eh_verdadeiro(item.get("atendido"))
                evidencia = item.get("evidencia")
                lista.adicionar_item(
                    item.get("requisito", ""),
                    f"Evidência: {evidencia}" if evidencia else "",
                    tag="OK" if ok else "FALTA",
                    cor=COR_OK if ok else COR_RUIM,
                )

        # ---- Pontos fortes e lacunas
        lista = self.listas["Pontos e lacunas"]
        lista.adicionar_titulo("Pontos fortes")
        fortes = r.get("pontos_fortes") or []
        for ponto in fortes:
            lista.adicionar_item(str(ponto), tag="FORTE", cor=COR_OK)
        if not fortes:
            lista.adicionar_item("Nenhum ponto forte listado.")

        lista.adicionar_titulo("Lacunas")
        lacunas = r.get("lacunas") or []
        for g in lacunas:
            g = como_dict(g, "item")
            como = g.get("como_mitigar")
            lista.adicionar_item(
                g.get("item", ""),
                f"Como mitigar: {como}" if como else "",
                tag="LACUNA",
                cor=COR_ALERTA,
            )
        if not lacunas:
            lista.adicionar_item("Nenhuma lacuna encontrada.")

        # ---- Palavras-chave
        lista = self.listas["Palavras-chave"]
        palavras = [str(p) for p in (r.get("palavras_chave_ats") or [])]
        if palavras:
            lista.adicionar_titulo("Inclua no currículo (onde fizer sentido e for verdade)")
            lista.adicionar_item(", ".join(palavras))
        else:
            lista.adicionar_vazio("Nenhuma palavra-chave sugerida.")

        # ---- Relatório
        self.ultimo_texto = formatar_resultado(r)
        self.txt_completo.configure(state="normal")
        self.txt_completo.delete("1.0", "end")
        self.txt_completo.insert("1.0", self.ultimo_texto)
        self.txt_completo.configure(state="disabled")

        self.btn_copiar.configure(state="normal")
        self.btn_salvar.configure(state="normal")
        self.abas.set("Resumo")
        self._ajustar_textos()

    def copiar_texto(self, texto: str):
        self.clipboard_clear()
        self.clipboard_append(texto)
        self._status("Sugestão copiada. Revise antes de colar no currículo.", COR_OK)

    def copiar(self):
        self.clipboard_clear()
        self.clipboard_append(self.ultimo_texto)
        self._status("Relatório copiado para a área de transferência.", COR_OK)

    def salvar(self):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="analise_vaga",
            filetypes=[("Texto", "*.txt"), ("Markdown", "*.md")],
        )
        if caminho:
            Path(caminho).write_text(self.ultimo_texto, encoding="utf-8")
            self._status(f"Salvo em {Path(caminho).name}.", COR_OK)

    # ------------------------------------------------------- responsividade
    def _ao_redimensionar(self, evento):
        if evento.widget is not self:
            return
        if self._job_resize:
            self.after_cancel(self._job_resize)
        self._job_resize = self.after(150, self._ajustar_textos)

    def _ajustar_textos(self):
        if not self.painel_resultado.winfo_ismapped():
            return
        largura = max(300, self.painel_resultado.winfo_width() - 90)
        self.cartao.definir_largura(largura - 230)
        for lista in self.listas.values():
            lista.definir_largura(largura)


if __name__ == "__main__":
    App().mainloop()