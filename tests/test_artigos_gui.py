#!/usr/bin/python
# encoding: utf-8

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from artigos_gui import lerConfig, montarConfig, parsearLista, serializarLista

LINHAS = [
    ('8826584877205264', 'Monalessa Perini Barcellos', '', 'professor'),
    ('9583314331960942', 'Daniel Cruz Cavalieri', '2020-2024', 'aluno doutorado'),
]


def test_ida_e_volta():
    assert parsearLista(serializarLista(LINHAS)) == LINHAS


def test_parse_tolerante():
    texto = (
        '# comentário puro\n'
        '\n'
        '1111111111 , Fulano de Tal , , professor   # com comentário no fim\n'
        '2222222222 ; Ciclano ; ; pós-doc\n'
        '3333333333\n'
        ', sem identificador , , professor\n'
    )
    assert parsearLista(texto) == [
        ('1111111111', 'Fulano de Tal', '', 'professor'),
        ('2222222222', 'Ciclano', '', 'pós-doc'),
        ('3333333333', '', '', ''),
    ]


def test_config():
    texto = montarConfig('Grupo X', 'lista.list', 'saida', 'cache', '1900', '2026')
    valores = lerConfig(texto)

    assert valores['nome'] == 'Grupo X'
    assert valores['anoInicial'] == '1900'
    assert valores['anoFinal'] == '2026'
    for campo in ('lista', 'saida', 'cache'):
        assert os.path.isabs(valores[campo]), f'{campo} deveria ser caminho absoluto'
    assert len(texto.strip().splitlines()) == 6, 'só as chaves que o artigos_csv.py usa'


def test_config_ignora_chaves_de_fora():
    assert lerConfig('relatorio-incluir_premio = sim\nglobal-nome_do_grupo = Y\n') == {'nome': 'Y'}


if __name__ == '__main__':
    test_ida_e_volta()
    test_parse_tolerante()
    test_config()
    test_config_ignora_chaves_de_fora()
    print('ok')
