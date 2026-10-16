# Analisador de Vagas

App desktop em Python que compara o seu currículo com uma vaga usando a API do
Google Gemini e mostra o que ajustar para aumentar suas chances.

## O que ele faz

- **Compatibilidade (%)** geral e por área: habilidades técnicas, experiência, formação e diferenciais
- **Requisitos** obrigatórios e desejáveis, com a evidência encontrada no currículo
- **Mudanças sugeridas** com prioridade, trecho **antes → depois** e botão para copiar
- **Pontos fortes, lacunas e palavras-chave** para sistemas de triagem (ATS)
- **Currículos base por categoria** (Back-end, Front-end, Mobile...), para escolher o certo em cada vaga
- Relatório que pode ser copiado ou salvo, modo claro/escuro e geração de `.exe` (Windows)

## Pré-requisitos

- Python 3.10 ou superior
- Uma chave da API do Gemini (há nível gratuito no Google AI Studio)

## Instalação

```powershell
git clone https://github.com/SouuSamuel/analisador-de-vagas.git
cd analisador-de-vagas
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

No Linux/macOS, ative o ambiente com `source venv/bin/activate`.

## Configurando a sua chave (a única coisa que você precisa trocar)

1. Gere uma chave em https://aistudio.google.com/app/apikey
2. No app, abra **⚙ Configurações**, cole a chave e clique em **Testar conexão**
3. Se algum modelo aparecer como indisponível, ajuste o nome dele e teste de novo (os nomes dos
   modelos mudam com o tempo). Depois clique em **Salvar**

A chave fica salva só no seu computador (`%APPDATA%\AnalisadorVagas\config.json`). Ela nunca vai
para o repositório. Se preferir, copie `.env.example` para `.env` e preencha.

## Como usar

1. Na tela **Currículos base**, crie categorias e associe um currículo (PDF, DOCX ou TXT) a cada uma
2. Na tela **Analisar**, escolha a categoria (ou "Outro arquivo…")
3. Cole a descrição da vaga e clique em **Analisar**

## Gerar o executável (Windows)

Com o ambiente virtual ativado:

```powershell
.\build_exe.bat
```

O programa fica em `dist\AnalisadorVagas\AnalisadorVagas.exe`.

## Limitações e avisos

- Sites como Indeed, LinkedIn e Gupy bloqueiam leitura automática de links: cole a descrição da vaga
- A porcentagem é uma **estimativa** gerada por IA, não uma medida exata. Revise cada sugestão
  antes de usar e nunca inclua no currículo algo que não seja verdade
- O texto do currículo e da vaga é enviado à API do Gemini. Consulte os termos de uso do Google
  e evite enviar dados sensíveis que você não queira compartilhar
- Testado no Windows. O código roda em outros sistemas, mas o `build_exe.bat` é para Windows
- Projeto pessoal e educacional, sem vínculo com o Google

## Estrutura

```
main.py                 interface principal
analisador.py           prompt, chamada ao Gemini e relatório
componentes.py          widgets da interface
tela_curriculos.py      tela de currículos base
tela_config.py          tela de configurações
curriculos.py           armazenamento dos currículos base
config.py, caminhos.py  configuração e pastas de dados
extrator_curriculo.py   leitura de PDF, DOCX e TXT
extrator_vaga.py        leitura de vagas por link
build_exe.bat           gera o executável
```

## Licença

**Gratuito para testes e uso pessoal. Não é permitido vender nem usar comercialmente.**

Você pode usar, estudar e modificar o projeto gratuitamente (inclusive nas suas candidaturas
de emprego). Vender, oferecer como serviço pago ou usar para gerar receita exige autorização
do autor. Detalhes no arquivo [`LICENSE`](LICENSE).