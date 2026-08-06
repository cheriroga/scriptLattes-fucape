#!/usr/bin/env python
# encoding: utf-8
#
# Interface gráfica para o artigos_csv.py: monta o .config e o .list por
# formulário, escolhe a pasta de saída e roda o script mostrando o progresso.
#
# Uso: python3 artigos_gui.py

import datetime
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

RAIZ = os.path.dirname(os.path.abspath(__file__))
COLUNAS = ('ID Lattes', 'Nome', 'Período', 'Rótulo')
ROTULOS = ('professor', 'aluno mestrado', 'aluno doutorado', 'pós-doc')
CABECALHO_LISTA = ('# id_lattes , nome , período , rótulo\n'
                   '# o rótulo vira a coluna "Rótulo" do CSV\n')
CHAVES_CONFIG = {
    'nome': 'global-nome_do_grupo',
    'lista': 'global-arquivo_de_entrada',
    'saida': 'global-diretorio_de_saida',
    'cache': 'global-diretorio_de_armazenamento_de_cvs',
    'anoInicial': 'global-itens_desde_o_ano',
    'anoFinal': 'global-itens_ate_o_ano',
}


# --------------------------------------------------------------------------- #
# conversões entre tabela, arquivo .list e arquivo .config
# --------------------------------------------------------------------------- #

def parsearLista(texto):
    """Texto no formato .list -> [(idLattes, nome, periodo, rotulo), ...].

    Mesma regra de separação do Grupo.__init__: comentário a partir do '#',
    separador vírgula com queda para ';' e depois tabulação, linha sem
    identificador é ignorada."""
    linhas = []
    for linha in texto.splitlines():
        linha = linha.partition('#')[0]

        partes = linha.split(',')
        if ';' in linha and len(partes) < 2:
            partes = linha.split(';')
        if '\t' in linha and len(partes) < 2:
            partes = linha.split('\t')

        partes = [parte.strip() for parte in partes] + ['', '', '', '']
        if partes[0]:
            linhas.append(tuple(partes[:4]))
    return linhas


def serializarLista(linhas):
    texto = CABECALHO_LISTA
    for idLattes, nome, periodo, rotulo in linhas:
        texto += f'{idLattes} , {nome} , {periodo} , {rotulo}\n'
    return texto


def montarConfig(nome, arquivoLista, diretorioSaida, diretorioCache, anoInicial, anoFinal):
    """Só as chaves que o artigos_csv.py usa: o resto tem default em
    Grupo.carregarParametrosPadrao, e chave desconhecida vira aviso na tela."""
    valores = {
        'nome': nome,
        'lista': os.path.abspath(arquivoLista),
        'saida': os.path.abspath(diretorioSaida),
        'cache': os.path.abspath(diretorioCache),
        'anoInicial': anoInicial,
        'anoFinal': anoFinal,
    }
    return ''.join(f'{CHAVES_CONFIG[campo]:<42}= {valores[campo]}\n' for campo in CHAVES_CONFIG)


def lerConfig(texto):
    """Arquivo .config -> {'nome': ..., 'saida': ...}, ignorando as chaves que
    não interessam ao artigos_csv.py."""
    porChave = {chave: campo for campo, chave in CHAVES_CONFIG.items()}
    valores = {}
    for linha in texto.splitlines():
        chave, igual, valor = linha.partition('#')[0].partition('=')
        if igual and chave.strip().lower() in porChave:
            valores[porChave[chave.strip().lower()]] = valor.strip()
    return valores


# --------------------------------------------------------------------------- #
# janela
# --------------------------------------------------------------------------- #

class Janela:
    def __init__(self, root):
        self.root = root
        self.processo = None
        self.fila = queue.Queue()
        root.title('scriptLattes — Artigos em periódicos')

        moldura = ttk.Frame(root, padding=10)
        moldura.pack(fill='both', expand=True)
        moldura.columnconfigure(1, weight=1)

        self.nome = self._campo(moldura, 0, 'Nome do grupo', 'Artigos em periódicos')
        self.saida = self._campo(moldura, 1, 'Pasta de saída', '',
                                 botao=('Escolher…', self.escolherSaida))
        self.cache = self._campo(moldura, 2, 'Cache de CVs', os.path.join(RAIZ, 'cache'),
                                 botao=('Escolher…', self.escolherCache))

        anos = ttk.Frame(moldura)
        anos.grid(row=3, column=0, columnspan=3, sticky='w', pady=(6, 0))
        ttk.Label(anos, text='Publicações de').pack(side='left')
        self.anoInicial = tk.StringVar(value='1900')
        self.anoFinal = tk.StringVar(value=str(datetime.datetime.now().year))
        ttk.Entry(anos, textvariable=self.anoInicial, width=6).pack(side='left', padx=4)
        ttk.Label(anos, text='até').pack(side='left')
        ttk.Entry(anos, textvariable=self.anoFinal, width=6).pack(side='left', padx=4)

        self._montarTabela(moldura)
        self._montarAcoes(moldura)
        self._montarLog(moldura)

        root.after(100, self._drenarFila)

    # ----- construção ------------------------------------------------------ #

    def _campo(self, moldura, linha, rotulo, valor, botao=None):
        ttk.Label(moldura, text=rotulo).grid(row=linha, column=0, sticky='w', pady=2)
        variavel = tk.StringVar(value=valor)
        ttk.Entry(moldura, textvariable=variavel).grid(row=linha, column=1, sticky='ew', padx=6)
        if botao:
            ttk.Button(moldura, text=botao[0], command=botao[1]).grid(row=linha, column=2)
        return variavel

    def _montarTabela(self, moldura):
        caixa = ttk.LabelFrame(moldura, text='Pesquisadores', padding=6)
        caixa.grid(row=4, column=0, columnspan=3, sticky='nsew', pady=(10, 0))
        caixa.columnconfigure(0, weight=1)
        caixa.rowconfigure(0, weight=1)
        moldura.rowconfigure(4, weight=1)

        self.tabela = ttk.Treeview(caixa, columns=COLUNAS, show='headings', height=8)
        for coluna in COLUNAS:
            self.tabela.heading(coluna, text=coluna)
            self.tabela.column(coluna, width=160 if coluna == 'Nome' else 120)
        self.tabela.grid(row=0, column=0, sticky='nsew')

        barra = ttk.Scrollbar(caixa, orient='vertical', command=self.tabela.yview)
        barra.grid(row=0, column=1, sticky='ns')
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.bind('<Double-1>', self.editarCelula)

        botoes = ttk.Frame(caixa)
        botoes.grid(row=1, column=0, columnspan=2, sticky='w', pady=(6, 0))
        ttk.Button(botoes, text='+ Adicionar', command=self.adicionarLinha).pack(side='left')
        ttk.Button(botoes, text='− Remover', command=self.removerLinha).pack(side='left', padx=6)
        ttk.Button(botoes, text='Editar como texto…', command=self.editarComoTexto).pack(side='left')
        ttk.Label(botoes, text='  (duplo clique edita a célula)').pack(side='left')

    def _montarAcoes(self, moldura):
        acoes = ttk.Frame(moldura)
        acoes.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(10, 0))
        ttk.Button(acoes, text='Abrir .config…', command=self.abrirConfig).pack(side='left')
        ttk.Button(acoes, text='Abrir pasta de saída', command=self.abrirPastaDeSaida).pack(side='left', padx=6)
        self.botaoParar = ttk.Button(acoes, text='Parar', command=self.parar, state='disabled')
        self.botaoParar.pack(side='right')
        self.botaoRodar = ttk.Button(acoes, text='Rodar', command=self.rodar)
        self.botaoRodar.pack(side='right', padx=6)

    def _montarLog(self, moldura):
        caixa = ttk.LabelFrame(moldura, text='Progresso', padding=6)
        caixa.grid(row=6, column=0, columnspan=3, sticky='nsew', pady=(10, 0))
        caixa.columnconfigure(0, weight=1)
        caixa.rowconfigure(0, weight=1)
        moldura.rowconfigure(6, weight=1)

        self.log = tk.Text(caixa, height=10, wrap='none', state='disabled')
        self.log.grid(row=0, column=0, sticky='nsew')
        barra = ttk.Scrollbar(caixa, orient='vertical', command=self.log.yview)
        barra.grid(row=0, column=1, sticky='ns')
        self.log.configure(yscrollcommand=barra.set)

    # ----- tabela ---------------------------------------------------------- #

    def linhasDaTabela(self):
        return [tuple(self.tabela.item(item, 'values')) for item in self.tabela.get_children()]

    def preencherTabela(self, linhas):
        self.tabela.delete(*self.tabela.get_children())
        for linha in linhas:
            self.tabela.insert('', 'end', values=linha)

    def adicionarLinha(self):
        item = self.tabela.insert('', 'end', values=('', '', '', ''))
        self.tabela.selection_set(item)
        self.tabela.see(item)

    def removerLinha(self):
        for item in self.tabela.selection():
            self.tabela.delete(item)

    def editarCelula(self, evento):
        if self.tabela.identify_region(evento.x, evento.y) != 'cell':
            return
        item = self.tabela.identify_row(evento.y)
        coluna = self.tabela.identify_column(evento.x)
        indice = int(coluna[1:]) - 1
        caixa = self.tabela.bbox(item, coluna)
        if not caixa:
            return

        valor = tk.StringVar(value=self.tabela.item(item, 'values')[indice])
        if COLUNAS[indice] == 'Rótulo':
            editor = ttk.Combobox(self.tabela, textvariable=valor, values=ROTULOS)
        else:
            editor = ttk.Entry(self.tabela, textvariable=valor)
        editor.place(x=caixa[0], y=caixa[1], width=caixa[2], height=caixa[3])
        editor.focus_set()

        def confirmar(_=None):
            valores = list(self.tabela.item(item, 'values'))
            valores[indice] = valor.get().strip()
            self.tabela.item(item, values=valores)
            editor.destroy()

        editor.bind('<Return>', confirmar)
        editor.bind('<FocusOut>', confirmar)
        editor.bind('<Escape>', lambda _: editor.destroy())

    def editarComoTexto(self):
        janela = tk.Toplevel(self.root)
        janela.title('Pesquisadores — edição como texto')
        janela.transient(self.root)

        ttk.Label(janela, text='Um pesquisador por linha. Comentários e espaçamento '
                               'não voltam para a tabela.').pack(anchor='w', padx=8, pady=(8, 0))
        texto = tk.Text(janela, width=80, height=20, wrap='none')
        texto.pack(fill='both', expand=True, padx=8, pady=8)
        texto.insert('1.0', serializarLista(self.linhasDaTabela()))

        def confirmar():
            self.preencherTabela(parsearLista(texto.get('1.0', 'end')))
            janela.destroy()

        botoes = ttk.Frame(janela)
        botoes.pack(fill='x', padx=8, pady=(0, 8))
        ttk.Button(botoes, text='Cancelar', command=janela.destroy).pack(side='right')
        ttk.Button(botoes, text='Confirmar', command=confirmar).pack(side='right', padx=6)

    # ----- arquivos -------------------------------------------------------- #

    def escolherSaida(self):
        diretorio = filedialog.askdirectory(title='Pasta de saída')
        if diretorio:
            self.saida.set(diretorio)

    def escolherCache(self):
        diretorio = filedialog.askdirectory(title='Pasta de cache dos CVs')
        if diretorio:
            self.cache.set(diretorio)

    def abrirConfig(self):
        caminho = filedialog.askopenfilename(title='Abrir configuração',
                                             filetypes=[('Configuração', '*.config'), ('Todos', '*')])
        if not caminho:
            return

        with open(caminho, encoding='utf-8') as arquivo:
            valores = lerConfig(arquivo.read())

        for campo, variavel in (('nome', self.nome), ('saida', self.saida), ('cache', self.cache),
                                ('anoInicial', self.anoInicial), ('anoFinal', self.anoFinal)):
            if valores.get(campo):
                variavel.set(valores[campo])

        lista = valores.get('lista', '')
        if lista and not os.path.isabs(lista):
            lista = os.path.join(os.path.dirname(os.path.abspath(caminho)), lista)
        if lista and os.path.isfile(lista):
            with open(lista, encoding='utf-8') as arquivo:
                self.preencherTabela(parsearLista(arquivo.read()))
        elif lista:
            messagebox.showwarning('Lista não encontrada',
                                   f'A configuração aponta para {lista}, que não existe.')

    def abrirPastaDeSaida(self):
        diretorio = self.saida.get().strip()
        if not os.path.isdir(diretorio):
            messagebox.showinfo('Pasta de saída', 'A pasta de saída ainda não existe.')
            return
        if sys.platform == 'win32':
            os.startfile(diretorio)
        else:
            subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', diretorio])

    # ----- execução -------------------------------------------------------- #

    def validar(self, linhas):
        if not self.saida.get().strip():
            return 'Escolha a pasta de saída.'
        if not linhas:
            return 'Adicione pelo menos um pesquisador.'
        for ano in (self.anoInicial.get(), self.anoFinal.get()):
            if not ano.strip().isdigit():
                return f'Ano inválido: "{ano}". Use quatro dígitos.'
        return None

    def rodar(self):
        if self.processo:
            return

        linhas = self.linhasDaTabela()
        erro = self.validar(linhas)
        if erro:
            messagebox.showerror('Não dá para rodar ainda', erro)
            return

        suspeitos = [linha[0] for linha in linhas if len(linha[0]) not in (10, 16)]
        if suspeitos and not messagebox.askyesno(
                'ID Lattes fora do padrão',
                'Estes identificadores não têm 10 nem 16 dígitos e provavelmente vão '
                f'falhar no download:\n\n{", ".join(suspeitos)}\n\nRodar mesmo assim?'):
            return

        diretorioSaida = os.path.abspath(self.saida.get().strip())
        try:
            os.makedirs(diretorioSaida, exist_ok=True)
            caminhoLista = os.path.join(diretorioSaida, 'pesquisadores.list')
            caminhoConfig = os.path.join(diretorioSaida, 'artigos.config')
            with open(caminhoLista, 'w', encoding='utf-8') as arquivo:
                arquivo.write(serializarLista(linhas))
            with open(caminhoConfig, 'w', encoding='utf-8') as arquivo:
                arquivo.write(montarConfig(self.nome.get(), caminhoLista, diretorioSaida,
                                           self.cache.get(), self.anoInicial.get(),
                                           self.anoFinal.get()))
        except OSError as e:
            messagebox.showerror('Erro ao gravar', str(e))
            return

        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self._escrever(f'[{caminhoConfig}]\n')

        # subprocesso (e não import): util.buscarArquivo lê sys.argv[1] para achar
        # o .config, o que só funciona quando o script é o programa principal.
        # '-u' mantém o log saindo linha a linha em vez de tudo no final.
        self.processo = subprocess.Popen(
            [sys.executable, '-u', os.path.join(RAIZ, 'artigos_csv.py'), caminhoConfig],
            cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace')
        threading.Thread(target=self._lerSaida, args=(self.processo,), daemon=True).start()

        self.botaoRodar.configure(state='disabled')
        self.botaoParar.configure(state='normal')

    def parar(self):
        if self.processo:
            self.processo.terminate()

    def _lerSaida(self, processo):
        for linha in processo.stdout:
            self.fila.put(linha)
        processo.wait()
        self.fila.put(None)  # sentinela de fim

    def _drenarFila(self):
        while True:
            try:
                linha = self.fila.get_nowait()
            except queue.Empty:
                break

            if linha is None:
                codigo = self.processo.returncode if self.processo else 0
                self.processo = None
                self.botaoRodar.configure(state='normal')
                self.botaoParar.configure(state='disabled')
                self._escrever(f'\n[FIM — código de saída {codigo}]\n')
                if codigo == 0:
                    messagebox.showinfo('Pronto', 'CSVs gerados em:\n'
                                        + os.path.abspath(self.saida.get().strip()))
                else:
                    messagebox.showerror('Falhou', 'O script terminou com erro. '
                                                   'Veja o progresso para o motivo.')
            else:
                self._escrever(linha)

        self.root.after(100, self._drenarFila)

    def _escrever(self, texto):
        self.log.configure(state='normal')
        self.log.insert('end', texto)
        self.log.see('end')
        self.log.configure(state='disabled')


if __name__ == '__main__':
    raiz = tk.Tk()
    Janela(raiz)
    raiz.mainloop()
