#!/usr/bin/python
# encoding: utf-8

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from artigos_csv import extrairClassificacao, extrairData, normalizarDoi

UM_RESULTADO = '''
<div class="results-grid">
  <a class="journal-card card-link" href="/detalhes/29169">
    <div class="jc-title">RAE REVISTA DE ADMINISTRACAO DE EMPRESAS</div>
    <div class="jc-meta"><strong>ISSN:</strong> 0034-7590, 2178-938X</div>
    <div class="jc-tags">
      <span class="pill" data-grade="B">CAPES: B</span>
      <span class="pill">ABDC: C</span>
      <span class="pill">ABS: 1</span>
      <span class="pill">JCR: Q4</span>
      <span class="pill">SJR: Q3</span>
      <span class="pill">SPELL: 10% melhores</span>
    </div>
  </a>
</div>
'''

DOIS_RESULTADOS = UM_RESULTADO + UM_RESULTADO

NENHUM_RESULTADO = '<div class="results-grid"><p>Nenhum Periódico Encontrado.</p></div>'


def test_um_resultado():
    assert extrairClassificacao(UM_RESULTADO) == {
        'CAPES': 'B', 'ABDC': 'C', 'ABS': '1',
        'JCR': 'Q4', 'SJR': 'Q3', 'SPELL': '10% melhores',
    }


def test_resultado_ambiguo_ou_ausente():
    assert extrairClassificacao(DOIS_RESULTADOS) == {}
    assert extrairClassificacao(NENHUM_RESULTADO) == {}


def test_normalizar_doi():
    assert normalizarDoi('http://dx.doi.org/10.1590/S0034-759020240505') == '10.1590/S0034-759020240505'
    assert normalizarDoi('https://doi.org/10.1016/j.infsof.2020.106310') == '10.1016/j.infsof.2020.106310'
    assert normalizarDoi(' 10.1590/S0034-7590 ') == '10.1590/S0034-7590'
    assert normalizarDoi('') == ''


def crossref(campo, partes):
    return json.dumps({'message': {campo: {'date-parts': [partes]}}})


def test_extrair_data():
    # a precisão é a que o Crossref der, sem inventar dia nem mês
    assert extrairData(crossref('published', [2024, 5, 12])) == '2024-05-12'
    assert extrairData(crossref('published', [2024, 5])) == '2024-05'
    assert extrairData(crossref('published', [2024])) == '2024'

    # 'published' é o campo novo; 'issued' cobre registro antigo que só tem ele
    assert extrairData(crossref('issued', [1998, 11])) == '1998-11'

    # DOI sem data, resposta vazia (rede caiu) e lixo não podem quebrar a linha
    assert extrairData(crossref('published', [])) == ''
    assert extrairData(json.dumps({'message': {}})) == ''
    assert extrairData('') == ''
    assert extrairData('<html>404</html>') == ''


if __name__ == '__main__':
    test_um_resultado()
    test_resultado_ambiguo_ou_ausente()
    test_normalizar_doi()
    test_extrair_data()
    print('ok')
