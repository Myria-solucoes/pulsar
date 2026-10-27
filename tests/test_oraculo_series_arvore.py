"""GEVAZP.OUT, VAZTOTGD.DAT, vazoesia.out, vazoesta.out contra os CSV e o REL.

Proveniência: F2-ARV-01..05 (PROVENIENCIA.md).
"""

import numpy as np
import pytest

from apoio import config, estat_geradas_rel, mes_estocastico, probvaz, vazoes
from pulsar import oraculos as O
from pulsar.oraculos import texto as T

PARES = [
    ("GEVAZP.OUT", "VAZOESI.CSV", O.ler_incrementais_geradas),
    ("VAZTOTGD.DAT", "VAZOEST.CSV", O.ler_totais_gerados),
    ("vazoesia.out", "VAZOESIA.CSV", O.ler_incrementais_artificiais),
    ("vazoesta.out", "VAZOESTA.CSV", O.ler_totais_artificiais),
]


@pytest.mark.parametrize("binario,csv,leitor", PARES, ids=[p[0] for p in PARES])
def test_igual_ao_csv_em_todos_os_valores(pacote, binario, csv, leitor):
    s = leitor(pacote.arq(binario))
    ordem, c = T.ler_csv_series(pacote.arq(csv))
    cfg = config(pacote.nome)
    # Um registro por cenário: tantos quantos as aberturas do período estocástico.
    assert s.n_cenarios == vazoes(pacote.nome).aberturas[-1]
    # Colunas na ordem NINT da configuração; o resto do registro é zero.
    assert [n for _, n in ordem] == [u.nome for u in cfg]
    assert np.all(s.valores[:, len(cfg):] == 0)
    mes = mes_estocastico(pacote.nome)
    x = c[:, :, mes - 1].T  # [cenario, usina]
    np.testing.assert_array_equal(np.round(s.valores[:, : len(cfg)], 2), x)


@pytest.mark.parametrize("binario,csv,leitor", PARES[2:], ids=[p[0] for p in PARES[2:]])
def test_csv_artificial_rotula_com_posto_artificial(pacote, binario, csv, leitor):
    ordem, _ = T.ler_csv_series(pacote.arq(csv))
    for (posto, _), u in zip(ordem, config(pacote.nome)):
        assert posto == u.coluna_ena


def test_amostra_contra_rel_media_gerada_totais(pacote):
    """Média ponderada pelas probabilidades do VAZTOTGD.DAT contra a linha GER
    das páginas 'RESULTADOS PARA VAZOES TOTALIZADAS' (1 casa)."""
    s = O.ler_totais_gerados(pacote.arq("VAZTOTGD.DAT"))
    p = probvaz(pacote.nome).astype(np.float64)
    rel = estat_geradas_rel(pacote.nome, "RESULTADOS PARA VAZOES TOTALIZADAS")
    mes = mes_estocastico(pacote.nome)
    n = 0
    for u in config(pacote.nome):
        if u.nome not in rel:
            continue
        media = float(p @ s.usina(u.nint))
        assert abs(media - rel[u.nome]["media_ger"][mes - 1]) <= 0.05 + 1e-9, u.nome
        n += 1
    assert n >= 150


def test_nomes_dos_arquivos_artificiais_em_minusculas(pacote):
    """F2-ARV-05: U19 §5.3.1.2/§5.3.2 chama os arquivos de VAZOESTA.OUT e
    VAZOESIA.OUT; no pacote publicado eles estão em minúsculas."""
    nomes = {p.name for p in pacote.dir.iterdir()}
    assert {"vazoesta.out", "vazoesia.out"} <= nomes
    assert not {"VAZOESTA.OUT", "VAZOESIA.OUT"} & nomes
