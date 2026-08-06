#!/usr/bin/env python
# encoding: utf-8
#
# Extrai apenas os artigos em periódicos dos CVs Lattes e gera CSVs, com a
# classificação do periódico (CAPES/ABDC/ABS/JCR/SJR/SPELL) obtida do
# periodicos-adm.com e a data de publicação obtida do Crossref pelo DOI.
#
# Uso: python3 artigos_csv.py exemplo/teste-01.config

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import bs4

from scriptLattes.grupo import Grupo
from scriptLattes.util import criarDiretorio

URL_BUSCA = 'https://periodicos-adm.com/?search_term={0}'
URL_CROSSREF = 'https://api.crossref.org/works/{0}'
CLASSIFICACOES = ['CAPES', 'ABDC', 'ABS', 'JCR', 'SJR', 'SPELL']
# as quatro datas de publicação do Crossref; as outras (created, deposited, indexed)
# são do registro no Crossref, não do artigo, e por isso ficam de fora
CAMPOS_DE_DATA = {
    'Publicado': 'published',
    'Emitido': 'issued',
    'Online': 'published-online',
    'Impresso': 'published-print',
}
COLUNAS = (['Pesquisador', 'Rótulo', 'ID Lattes', 'Ano'] + list(CAMPOS_DE_DATA)
           + ['Título', 'Revista', 'ISSN', 'Volume', 'Número', 'Páginas', 'DOI', 'Autores']
           + CLASSIFICACOES + ['Classificado por'])


def extrairClassificacao(html):
    """Lê o card de resultado do periodicos-adm.com.

    Retorna {'CAPES': 'B', 'ABDC': 'C', ...} quando a busca traz exatamente um
    periódico; {} quando não traz nenhum ou traz mais de um (ambíguo)."""
    cards = bs4.BeautifulSoup(html, 'html.parser').select('.journal-card')
    if len(cards) != 1:
        return {}

    classificacao = {}
    for pill in cards[0].select('.pill'):
        nome, _, valor = pill.get_text().partition(':')
        nome = nome.strip()
        if nome in CLASSIFICACOES:
            classificacao[nome] = valor.strip()
    return classificacao


def normalizarDoi(doi):
    """O Lattes guarda o DOI como URL; o Crossref quer só o identificador.

    'http://dx.doi.org/10.1590/S0034-7590' -> '10.1590/S0034-7590'"""
    doi = doi.strip()
    for prefixo in ('http://', 'https://'):
        if doi.startswith(prefixo):
            doi = doi[len(prefixo):].partition('/')[2]  # tira o host
    return doi.strip('/')


def formatarData(partes):
    """['2024', 5, 12] -> '2024-05-12'. Mantém a precisão que veio: o Crossref
    às vezes dá só o ano, ou ano e mês."""
    if not partes or not partes[0]:
        return ''
    return '-'.join(f'{int(n):02d}' if i else str(int(n)) for i, n in enumerate(partes[:3]))


def extrairDatas(corpo):
    """As quatro datas de publicação do JSON do Crossref, só as preenchidas:
    {'Publicado': '2023-09-30', 'Emitido': '2023-09-30', ...}"""
    try:
        mensagem = json.loads(corpo)['message']
    except (ValueError, KeyError, TypeError):
        return {}

    datas = {}
    for coluna, campo in CAMPOS_DE_DATA.items():
        data = formatarData(((mensagem.get(campo) or {}).get('date-parts') or [[]])[0])
        if data:
            datas[coluna] = data
    return datas


class BaseDeClassificacoes:
    """Dicionário ISSN/nome/DOI -> classificação ou data, persistido em JSON.

    Quanto mais o script roda, menos consultas: uma chave presente (mesmo vazia)
    nunca é rebuscada.
    # ponytail: miss fica cacheado para sempre; apagar o .json quando o site
    # publicar uma atualização (o rodapé dele mostra a data da última)."""

    def __init__(self, caminho):
        self.caminho = caminho
        self.dados = {}
        self.consultas = 0
        if os.path.exists(caminho):
            with open(caminho, encoding='utf-8') as f:
                self.dados = json.load(f)

    def _consultar(self, chave, url, extrair, descricao):
        vazio = extrair('')
        if isinstance(self.dados.get(chave), type(vazio)):
            return self.dados[chave]

        time.sleep(1)  # cortesia com quem serve: 1 requisição por segundo
        print(f'   buscando {descricao}')
        self.consultas += 1
        try:
            with urllib.request.urlopen(url, timeout=30) as resposta:
                corpo = resposta.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print(f'   [AVISO] falha ao consultar {descricao}: {e}')
                return vazio  # erro passageiro: não cacheia, tenta de novo depois
            corpo = ''  # 404 é resposta definitiva: cacheia o vazio
        except Exception as e:
            print(f'   [AVISO] falha ao consultar {descricao}: {e}')
            return vazio  # não cacheia falha de rede

        self.dados[chave] = extrair(corpo)
        return self.dados[chave]

    def classificar(self, issn, revista):
        """Retorna (classificação, origem). Origem: 'issn', 'nome' ou ''."""
        if issn:
            classificacao = self._buscar(f'issn:{issn}', issn)
            if classificacao:
                return classificacao, 'issn'

        if revista:
            classificacao = self._buscar(f'nome:{revista.upper()}', revista)
            if classificacao:
                return classificacao, 'nome'

        return {}, ''

    def _buscar(self, chave, termo):
        return self._consultar(chave, URL_BUSCA.format(urllib.parse.quote(termo)),
                               extrairClassificacao, f'classificação: {termo}')

    def datasDoArtigo(self, doi):
        """Datas de publicação pelo DOI, via Crossref. Sem DOI ou sem registro lá, {}."""
        doi = normalizarDoi(doi)
        if not doi:
            return {}
        return self._consultar(f'doi:{doi}', URL_CROSSREF.format(urllib.parse.quote(doi)),
                               extrairDatas, f'datas: {doi}')

    def salvar(self):
        with open(self.caminho, 'w', encoding='utf-8') as f:
            json.dump(self.dados, f, ensure_ascii=False, indent=1, sort_keys=True)


def linhaDoArtigo(membro, artigo, base):
    classificacao, origem = base.classificar(artigo.issn, artigo.revista)
    datas = base.datasDoArtigo(artigo.doi)
    linha = {
        'Pesquisador': membro.nomeCompleto,
        # 4a coluna do arquivo .list: professor, mestrado, doutorado, pós-doc, ...
        'Rótulo': membro.rotulo,
        'ID Lattes': membro.idLattes,
        'Ano': artigo.ano,
        'Título': artigo.titulo,
        'Revista': artigo.revista,
        'ISSN': artigo.issn,
        'Volume': artigo.volume,
        'Número': artigo.numero,
        'Páginas': artigo.paginas,
        'DOI': artigo.doi,
        'Autores': artigo.autores,
        'Classificado por': origem,
    }
    linha.update({c: classificacao.get(c, '') for c in CLASSIFICACOES})
    linha.update({c: datas.get(c, '') for c in CAMPOS_DE_DATA})
    return linha


def salvarCSV(caminho, linhas):
    with open(caminho, 'w', encoding='utf-8', newline='') as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(linhas)


def nomeDeArquivo(membro):
    # mesmo padrão dos JSONs individuais (grupo.gerarArquivosJSONIndividuais)
    nome = re.sub(r'[^\w\s-]', '', membro.nomeCompleto.strip())
    nome = re.sub(r'[-\s]+', '-', nome)
    return f'{membro.idMembro:02d}_{nome}_{membro.idLattes}.csv'


def executar(arquivoConfiguracao):
    grupo = Grupo(arquivoConfiguracao)
    diretorioSaida = grupo.obterParametro('global-diretorio_de_saida')
    if not criarDiretorio(diretorioSaida):
        return
    diretorioIndividual = os.path.join(diretorioSaida, 'artigos')
    criarDiretorio(diretorioIndividual)

    grupo.carregarDadosCVLattes()

    # na raiz do repo (e não em cache/, que é ignorado pelo git): a base é versionada
    # e compartilhada entre quem usa o script
    base = BaseDeClassificacoes(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             'classificacoes-periodicos.json'))
    todasAsLinhas = []
    try:
        for membro in grupo.listaDeMembros:
            print(f'\n[CLASSIFICANDO ARTIGOS: {membro.nomeCompleto}]')
            linhas = [linhaDoArtigo(membro, artigo, base)
                      for artigo in membro.listaArtigoEmPeriodico]
            salvarCSV(os.path.join(diretorioIndividual, nomeDeArquivo(membro)), linhas)
            todasAsLinhas.extend(linhas)
    finally:
        base.salvar()  # não perde o que já foi consultado se algo falhar no meio

    salvarCSV(os.path.join(diretorioSaida, 'artigos_periodicos.csv'), todasAsLinhas)

    print(f'\n[{len(todasAsLinhas)} artigos em {len(grupo.listaDeMembros)} pesquisadores]')
    print(f'[CSV do grupo: {os.path.join(diretorioSaida, "artigos_periodicos.csv")}]')
    print(f'[CSV individuais: {diretorioIndividual}]')
    periodicos = sum(1 for chave in base.dados if not chave.startswith('doi:'))
    print(f'[Base local: {base.caminho} ({periodicos} periódicos, '
          f'{len(base.dados) - periodicos} DOIs, {base.consultas} consultas nesta execução)]')


if __name__ == '__main__':
    executar(sys.argv[1])
