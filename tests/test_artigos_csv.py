#!/usr/bin/python
# encoding: utf-8

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from artigos_csv import extrairClassificacao

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


if __name__ == '__main__':
    test_um_resultado()
    test_resultado_ambiguo_ou_ausente()
    print('ok')
