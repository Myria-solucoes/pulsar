"""GEVAZP.OUT, VAZTOTGD.DAT, vazoesia.out, vazoesta.out contra os CSV e o REL.

Proveniência: F2-ARV-01..05 (PROVENIENCIA.md).
"""

import numpy as np
import pytest

import apoio
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
    assert n >= 140


def test_nomes_dos_arquivos_artificiais_em_minusculas(pacote):
    """F2-ARV-05: U19 §5.3.1.2/§5.3.2 chama os arquivos de VAZOESTA.OUT e
    VAZOESIA.OUT; no pacote publicado eles estão em minúsculas."""
    nomes = {p.name for p in pacote.dir.iterdir()}
    assert {"vazoesta.out", "vazoesia.out"} <= nomes
    assert not {"VAZOESTA.OUT", "VAZOESIA.OUT"} & nomes


# P-LN3-03 (lacuna L8): incrementais negativas nos cenários publicados.
NEGATIVAS = {"202312_pmo": {"SOBRADINHO"}, "202411_pmo": {"TRES IRMAOS"},
             "202511_pmo": {"TRES IRMAOS"}, "202512_pmo": {"SOBRADINHO"}}


def test_incrementais_negativas_no_gevazp_out(pacote):
    """P-LN3-03: nos 61 pacotes só quatro têm incremental gerada negativa
    no GEVAZP.OUT. SOBRADINHO (202312, 202512) é a usina da defasagem linear
    (P-ESP-10, combinação do lateral com os totais de montante), sem
    lognormal própria. TRES IRMAOS (202411 e 202511, mês estocástico
    dezembro) é série com modelo PAR(p)-A (índice do correli.out), tem
    cenários até -27 m³/s e o negativo já está nos totais: total menos o
    total de NAVANHANDAVA no VAZTOTGD.DAT dá a incremental em todos os bits,
    então não vem do recálculo da F6-INC-01. Com M_t = 0 a lognormal só
    gera Z > 0: ao menos ali o limite inferior oficial é negativo."""
    import base
    from test_t8_totalizacao import _oficiais

    cfg = base.configuracao(pacote.nome)
    of = _oficiais(pacote.nome)
    inc, tot = of["incrementais"], of["totais"]
    idx = {u.numero: i for i, u in enumerate(cfg.completa)}
    neg = {u.nome_str for i, u in enumerate(cfg.completa) if inc[:, i].min() < -1e-6}
    assert neg == NEGATIVAS.get(pacote.nome, set())
    if "TRES IRMAOS" in neg:
        u = next(u for u in cfg.completa if u.nome_str == "TRES IRMAOS")
        i = idx[u.numero]
        assert apoio.nint_por_nome(pacote.nome)[u.nome_str] in apoio.correli(pacote.nome).indice
        recalc = tot[:, i] - sum(tot[:, idx[m]] for m in cfg.montante(u.numero))
        assert np.array_equal(recalc, inc[:, i])
        assert inc[:, i].min() < -20 and (inc[:, i] < 0).sum() >= 20
