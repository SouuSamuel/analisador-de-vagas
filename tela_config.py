import threading
import webbrowser
from tkinter import messagebox

import customtkinter as ctk
from google import genai
from google.genai import errors

import config
from caminhos import PASTA_DADOS
from componentes import COR_OK, COR_RUIM, TEXTO_SUAVE


def _traduzir_erro(codigo) -> str:
    return {
        404: "modelo não encontrado ou indisponível",
        429: "limite de uso atingido",
        500: "erro no servidor do Google",
        503: "sobrecarregado agora (temporário)",
        400: "chave inválida ou requisição recusada",
        401: "chave inválida",
        403: "chave sem permissão",
    }.get(codigo, f"erro {codigo}")


class TelaConfig(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Configurações")
        self.geometry("540x560")
        self.resizable(False, False)
        self.transient(master)
        self.after(200, self._focar)

        cfg = config.carregar()
        negrito = ctk.CTkFont(size=13, weight="bold")

        ctk.CTkLabel(self, text="Configurações", font=ctk.CTkFont(size=20, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 0)
        )

        ctk.CTkLabel(self, text="Chave da API do Gemini", font=negrito).pack(
            anchor="w", padx=20, pady=(16, 4)
        )
        self.entry_chave = ctk.CTkEntry(self, show="•")
        self.entry_chave.insert(0, cfg["api_key"])
        self.entry_chave.pack(fill="x", padx=20)

        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(fill="x", padx=20, pady=(6, 0))
        self.var_mostrar = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            linha, text="Mostrar chave", variable=self.var_mostrar, command=self._alternar_chave
        ).pack(side="left")
        ctk.CTkButton(
            linha, text="Gerar chave no Google AI Studio", fg_color="transparent",
            border_width=1, text_color=("gray10", "gray90"),
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
        ).pack(side="right")

        ctk.CTkLabel(self, text="Modelo principal", font=negrito).pack(
            anchor="w", padx=20, pady=(18, 4)
        )
        self.entry_modelo = ctk.CTkEntry(self)
        self.entry_modelo.insert(0, cfg["modelo"])
        self.entry_modelo.pack(fill="x", padx=20)

        ctk.CTkLabel(self, text="Modelos reserva (separe por vírgula)", font=negrito).pack(
            anchor="w", padx=20, pady=(14, 4)
        )
        self.entry_reserva = ctk.CTkEntry(self)
        self.entry_reserva.insert(0, ", ".join(cfg["modelos_reserva"]))
        self.entry_reserva.pack(fill="x", padx=20)

        ctk.CTkLabel(
            self,
            text=f"Os dados do app ficam em:\n{PASTA_DADOS}",
            anchor="w", justify="left", text_color=TEXTO_SUAVE, wraplength=480,
        ).pack(anchor="w", padx=20, pady=(14, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=20, pady=(16, 6))
        self.btn_testar = ctk.CTkButton(
            botoes, text="Testar conexão", fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), command=self._testar,
        )
        self.btn_testar.pack(side="left")
        ctk.CTkButton(botoes, text="Salvar", command=self._salvar).pack(side="right")

        self.lbl_resultado = ctk.CTkLabel(
            self, text="", anchor="w", justify="left", wraplength=480
        )
        self.lbl_resultado.pack(anchor="w", padx=20, pady=(4, 10))

    def _focar(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass

    def _alternar_chave(self):
        self.entry_chave.configure(show="" if self.var_mostrar.get() else "•")

    def _modelos_digitados(self) -> list:
        principal = config.limpar(self.entry_modelo.get())
        reservas = [config.limpar(m) for m in self.entry_reserva.get().split(",")]
        lista = [principal] + [m for m in reservas if m]
        return [m for i, m in enumerate(lista) if m and m not in lista[:i]]

    def _testar(self):
        chave = config.limpar(self.entry_chave.get())
        modelos = self._modelos_digitados()
        if not chave or not modelos:
            self.lbl_resultado.configure(text="Informe a chave e ao menos um modelo.", text_color=COR_RUIM)
            return
        self.btn_testar.configure(state="disabled", text="Testando...")
        self.lbl_resultado.configure(text="Testando cada modelo...", text_color=TEXTO_SUAVE)
        threading.Thread(target=self._testar_thread, args=(chave, modelos), daemon=True).start()

    def _testar_thread(self, chave, modelos):
        linhas, algum_ok = [], False
        client = genai.Client(api_key=chave)
        for nome in modelos:
            try:
                client.models.generate_content(model=nome, contents="Responda apenas: ok")
                linhas.append(f"[OK]  {nome}")
                algum_ok = True
            except errors.APIError as e:
                linhas.append(f"[X]   {nome}: {_traduzir_erro(e.code)}")
            except Exception as e:
                linhas.append(f"[X]   {nome}: {str(e)[:80]}")
        try:
            self.after(0, self._mostrar_teste, "\n".join(linhas), algum_ok)
        except Exception:
            pass  # a janela foi fechada durante o teste

    def _mostrar_teste(self, texto, algum_ok):
        self.btn_testar.configure(state="normal", text="Testar conexão")
        self.lbl_resultado.configure(text=texto, text_color=COR_OK if algum_ok else COR_RUIM)

    def _salvar(self):
        chave = config.limpar(self.entry_chave.get())
        modelos = self._modelos_digitados()
        if not chave:
            messagebox.showwarning("Atenção", "Cole a chave da API do Gemini.", parent=self)
            return
        if not modelos:
            messagebox.showwarning("Atenção", "Informe o modelo principal.", parent=self)
            return
        config.salvar(chave, modelos[0], modelos[1:])
        messagebox.showinfo("Configurações", "Configurações salvas.", parent=self)
        self.destroy()