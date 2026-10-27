"""QPAST.DAT e vazaoanual.out contra as tabelas de tendência do GEVAZP.REL.

Proveniência: F2-QP-01..05, F2-VA-01..03.
"""

import numpy as np
import pytest

from apoio import config, mes_estocastico, qpast, tendencia_rel, vazoes
from pulsar import oraculos as O


def test_qpast_incremental_igual_ao_rel(pacote):
    """Registros 1-12 = 'VAZOES INCREMENTAIS PARA A TENDENCIA ... POSTOS PRINCIPAIS'."""
    q = qpast(pacote.nome)
    tab = tendencia_rel(pacote.nome)["incrementais_principais"]
    assert len(tab) > 150
    for posto, (nome, v) in tab.items():
        np.testing.assert_array_equal(np.round(q.incrementais_do_posto(posto), 2), v, err_msg=nome)


def test_qpast_total_igual_ao_rel(pacote):
    """Registros 13-24 = 'VAZOES FORNECIDAS PARA A TENDENCIA HIDROLOGICA'."""
    q = qpast(pacote.nome)
    tab = tendencia_rel(pacote.nome)["fornecidas"]
    for posto, (nome, v) in tab.items():
        np.testing.assert_array_equal(np.round(q.totais_do_posto(posto), 2), v, err_msg=nome)


def test_qpast_fora_dos_principais_incremental_repete_total(pacote):
    q = qpast(pacote.nome)
    principais = set(tendencia_rel(pacote.nome)["incrementais_principais"])
    for posto in range(1, q.total.shape[1] + 1):
        if posto not in principais and q.totais_do_posto(posto).any():
            np.testing.assert_array_equal(q.incrementais_do_posto(posto), q.totais_do_posto(posto))


def test_qpast_exemplo_camargos_202609(pacote):
    if pacote.nome != "202609":
        pytest.skip("amostra legível escrita para o 202609")
    q = qpast(pacote.nome)
    # GEVAZP.REL: "1 CAMARGOS 117.00 148.00 ... 44.90 34.00 46.00 69.00"
    assert q.incremental_mensal(1, 9) == 44.9
    assert q.incremental_mensal(1, 10) == 34.0
    # FURNAS (posto 6): incremental 659 e total 908 em janeiro
    assert q.incremental_mensal(6, 1) == 659.0 and q.total_mensal(6, 1) == 908.0


def test_vazaoanual_e_media_dos_12_meses_da_tendencia(pacote):
    """vazaoanual.out = média das 12 incrementais da tabela de tendência do REL
    (2 casas), igual em todos os cenários; zero nas usinas PN."""
    a = O.ler_media_anual_anterior(pacote.arq("vazaoanual.out"))
    tab = tendencia_rel(pacote.nome)["incrementais_principais"]
    n = 0
    for u in config(pacote.nome):
        col = a.usina(u.nint)
        assert np.all(col == col[0]), u.nome
        if u.status == "PN":
            assert np.all(col == 0), u.nome
        elif u.posto in tab:
            assert abs(col[0] - tab[u.posto][1].mean()) <= 0.005 + 1e-9, u.nome
            n += 1
    assert n > 150


def test_vazaoanual_bits_soma_em_ordem_de_calendario(pacote):
    """INFERIDO F2-VA-03: com os 12 meses indexados pelo calendário
    (jan..dez) e divisão por 12, reproduz todos os bits. A ordem da soma
    dentro do calendário NÃO é discriminada: a soma sequencial e a soma por
    blocos da np.sum dão os mesmos bits nestes decks."""
    a = O.ler_media_anual_anterior(pacote.arq("vazaoanual.out"))
    q = qpast(pacote.nome)
    for u in config(pacote.nome):
        if u.status == "PN":
            continue
        s = 0.0
        for m in range(1, 13):
            s += q.incremental_mensal(u.posto, m)
        assert np.all(a.usina(u.nint) == s / 12), u.nome
        assert np.all(a.usina(u.nint) == np.sum(q.incrementais_do_posto(u.posto)) / 12), u.nome


def _ano_inicial_historico(pacote) -> int:
    with open(pacote.arq("GEVAZP.REL"), encoding="latin-1") as f:
        for linha in f:
            if "ANO INICIAL DO HISTORICO DE VAZOES" in linha:
                return int(linha.split()[-1])
    raise AssertionError("ano inicial do histórico não encontrado")


def test_qpast_mes_inicial_da_tendencia_e_o_mes_estocastico(pacote):
    """F2-QP-03: 'MES INICIAL DA TENDENCIA HIDROLOGICA' do REL = mês estocástico;
    a janela de 12 meses começa nele (no ano anterior) e vai até o mês inicial."""
    with open(pacote.arq("GEVAZP.REL"), encoding="latin-1") as f:
        mes = next(int(l.split()[-1]) for l in f if "MES INICIAL DA TENDENCIA HIDROLOGICA" in l)
    assert mes == mes_estocastico(pacote.nome)


def test_qpast_anos_dos_meses_pelo_historico(pacote):
    """F2-QP-03: totais do QPAST contra o VAZOES.DAT do pacote. Meses antes do
    mês inicial do estudo são do ano do estudo; meses depois dele, do ano
    anterior; o mês inicial é a média das semanas e não está no histórico.
    VAZOES.DAT lido como int32, um registro de NPOS postos por mês desde o
    ano inicial do histórico (F2-QP-05)."""
    v = vazoes(pacote.nome)
    mi, ano = v.calendario.mes_inicial, v.calendario.ano_inicial
    a0 = _ano_inicial_historico(pacote)
    h = np.fromfile(pacote.arq("VAZOES.DAT"), "<i4").reshape(-1, 12, v.npos)
    q = qpast(pacote.nome)
    postos = sorted(tendencia_rel(pacote.nome)["fornecidas"])
    assert len(postos) > 150
    for m in range(1, 13):
        if m == mi:
            continue
        a = ano if m < mi else ano - 1
        outro = ano - 1 if m < mi else ano
        x = q.total[m - 1, [p - 1 for p in postos]]
        np.testing.assert_array_equal(x, h[a - a0, m - 1, [p - 1 for p in postos]], err_msg=f"mês {m}")
        # e o ano alternativo não serve
        assert not np.array_equal(x, h[outro - a0, m - 1, [p - 1 for p in postos]]), m
