# scriptLattes — FUCAPE

Fork do [scriptLattes](https://github.com/jpmenachalco/scriptLattes), de Jesús P. Mena-Chalco e Roberto M. Cesar-Jr.

O scriptLattes original lê Currículos Lattes e gera um site completo: todas as produções, orientações, projetos, grafos de coautoria, mapas. **Este fork acrescenta um caminho curto**, para quem quer só uma coisa: a lista de **artigos publicados em periódicos**, em planilha, já com a classificação de cada revista e as datas de publicação.

O programa original continua aqui e funcionando. Para entender tudo que ele faz, leia o [README do repositório original](https://github.com/jpmenachalco/scriptLattes#readme).

## Como funciona

```
   arquivo .list                 Lattes (CNPq)
   quem são os          ──────►  baixa o currículo HTML de cada um
   pesquisadores                 (Chrome automatizado, uma vez só — depois fica em cache/)
                                        │
                                        ▼
                                 lê só os "Artigos completos publicados em periódicos"
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                                       ▼
          periodicos-adm.com                            Crossref
          classificação da revista                      datas de publicação
          (busca pelo ISSN)                             (busca pelo DOI)
                    └───────────────────┬───────────────────┘
                                        ▼
                                 artigos_periodicos.csv  (todo mundo)
                                 artigos/*.csv           (um por pesquisador)
```

Cada consulta feita fica guardada em `classificacoes-periodicos.json`. Uma revista ou um DOI que já está lá **nunca é consultado de novo** — a segunda execução não acessa a internet.

## Instalação

Precisa de **Python 3.10+** e do **Google Chrome** (ou Chromium) instalado.

**Linux / macOS**

```bash
git clone https://github.com/cheriroga/scriptLattes-fucape.git
cd scriptLattes-fucape
make install
```

**Windows** (o Makefile não funciona lá)

```powershell
git clone https://github.com/cheriroga/scriptLattes-fucape.git
cd scriptLattes-fucape

python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

O ChromeDriver é baixado sozinho na primeira execução, pelo Selenium Manager, na versão certa para o seu Chrome. Não precisa instalar nada à mão.

No Fedora/RHEL, se a janela do programa não abrir: `sudo dnf install python3-tkinter`.

## Usando pela janela (mais fácil)

```bash
source venv/bin/activate            # Linux/macOS
python3 artigos_gui.py
```

```powershell
venv\Scripts\python.exe artigos_gui.py    # Windows
```

Na janela você:

1. dá um **nome ao grupo** e escolhe **onde salvar**;
2. monta a **lista de pesquisadores** na tabela — duplo clique edita a célula, `+ Adicionar` cria linha. A coluna **Rótulo** (professor, aluno mestrado, aluno doutorado, pós-doc…) vira uma coluna da planilha, para separar os tipos depois;
3. clica em **Rodar** e acompanha o progresso ali mesmo.

Para colar a lista de uma planilha de uma vez, use **Editar como texto…**.

Cada grupo ganha uma pasta só sua:

```
<onde salvar>/
└── FUCAPE-2026/                 ← o nome que você deu ao grupo
    ├── artigos.config           ← configuração, gerada pela janela
    ├── pesquisadores.list       ← a lista, gerada pela janela
    ├── artigos_periodicos.csv   ← todos os pesquisadores
    └── artigos/
        └── 00_Nome_1234567890123456.csv
```

A janela **lembra do que você preencheu**: ao rodar ou fechar, tudo volta na próxima abertura. **Abrir .config…** recarrega um trabalho anterior, para pular entre grupos.

## Usando pelo terminal

Mesma coisa, sem janela. Você escreve os dois arquivos à mão:

```bash
python3 artigos_csv.py caminho/para/artigos.config
```

O `.list` é uma linha por pesquisador, separado por vírgula:

```
# id_lattes , nome , período , rótulo
8826584877205264 , Monalessa Perini Barcellos , , professor
9583314331960942 , Daniel Cruz Cavalieri      , , aluno doutorado
```

O `.config` precisa só destas seis linhas (o resto tem valor padrão):

```
global-nome_do_grupo                      = FUCAPE 2026
global-arquivo_de_entrada                 = /caminho/pesquisadores.list
global-diretorio_de_saida                 = /caminho/FUCAPE-2026
global-diretorio_de_armazenamento_de_cvs  = /caminho/cache
global-itens_desde_o_ano                  = 1900
global-itens_ate_o_ano                    = 2026
```

## O que vem na planilha

| Coluna | De onde vem |
| --- | --- |
| `Pesquisador`, `Rótulo`, `ID Lattes` | da sua lista |
| `Ano` | Lattes |
| `Publicado`, `Emitido`, `Online`, `Impresso` | Crossref, pelo DOI |
| `Título`, `Revista`, `ISSN`, `Volume`, `Número`, `Páginas`, `DOI`, `Autores` | Lattes |
| `CAPES`, `ABDC`, `ABS`, `JCR`, `SJR`, `SPELL` | periodicos-adm.com |
| `Classificado por` | `issn`, `nome` ou vazio — como a revista foi encontrada |

Uma linha por pesquisador **por artigo**: um artigo escrito por dois membros do grupo aparece duas vezes, uma para cada.

### Classificação da revista

Vem do [periodicos-adm.com](https://periodicos-adm.com/): CAPES (classificação 2025–2028, que substituiu o Qualis), ABDC, ABS, JCR, SJR e SPELL.

A busca é pelo **ISSN**. Sem ISSN, ou sem resultado, tenta pelo **nome da revista**. Nos dois casos só aceita quando encontra **uma revista só** — busca ambígua deixa em branco em vez de arriscar a revista errada. A coluna `Classificado por` mostra qual caminho funcionou.

Como o site cobre a área 27 (Administração, Contábeis e Turismo), revista de outra área costuma vir só com CAPES, JCR e SJR.

### As quatro datas

O Lattes guarda **só o ano**. Para ter mês e dia, o script pergunta ao [Crossref](https://api.crossref.org/) usando o DOI:

| Coluna | O que é |
| --- | --- |
| `Publicado` | a mais antiga entre online e impresso |
| `Emitido` | mesma ideia, campo antigo do Crossref |
| `Online` | quando saiu na internet |
| `Impresso` | data do fascículo impresso |

Cada uma sai na precisão que existir: `2023-09-30`, `2021-12` ou `2024`. Vazio quer dizer que aquele campo não existe no registro — revista só digital não tem `Impresso`, e vice-versa.

**As datas divergem entre si e do Lattes de propósito.** Artigo publicado online em dezembro sai no fascículo do ano seguinte: a planilha mostra `Ano 2023` com `Publicado 2022-12-23`. Por isso as cinco colunas convivem — escolha a que serve ao seu relatório.

Tudo vazio significa que o artigo não tem DOI no Lattes, ou que o DOI não está no Crossref (comum em revista brasileira que registra em outra agência).

## O scriptLattes completo

Continua funcionando, e gera o site com tudo:

```bash
python3 scriptLattes.py exemplo/teste-01.config
```

O `.config` dele tem dezenas de opções (tipos de produção, grafos, métricas, filtro por termos). Veja `exemplo/teste-01.config` e o [README do projeto original](https://github.com/jpmenachalco/scriptLattes#readme).

## Testes

```bash
venv/bin/python tests/test_artigos_csv.py
venv/bin/python tests/test_artigos_gui.py
```

Não acessam a internet.

## Créditos

O scriptLattes é software livre (GNU GPL), idealizado por Jesús P. Mena-Chalco e Roberto M. Cesar-Jr em 2005 (IME/USP). Ao usar, cite:

- J. P. Mena-Chalco e R. M. Cesar-Jr. *scriptLattes: An open-source knowledge extraction system from the Lattes platform.* Journal of the Brazilian Computer Society, vol. 15, n. 4, páginas 31–39, 2009. [doi:10.1007/BF03194511](http://dx.doi.org/10.1007/BF03194511)
- J. P. Mena-Chalco e R. M. Cesar-Jr. *Prospecção de dados acadêmicos de currículos Lattes através de scriptLattes.* Em *Bibliometria e Cientometria: reflexões teóricas e interfaces*. São Carlos: Pedro & João, páginas 109–128, 2013. [doi:10.13140/RG.2.1.5183.8561](http://dx.doi.org/10.13140/RG.2.1.5183.8561)

Dúvidas sobre o projeto original: [Discord](https://discord.gg/Xz8NZ3kBc3) · jesus.mena@ufabc.edu.br

O scriptLattes não tem vínculo com o CNPq. É um esforço independente para automatizar a compilação de informações que já são públicas nos Currículos Lattes; o CNPq não presta suporte à ferramenta.
