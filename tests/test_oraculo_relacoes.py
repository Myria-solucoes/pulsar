"""Relações numéricas entre os arquivos do pacote, úteis às outras frentes.

Proveniência: F2-REL-01..02.
"""

import numpy as np
import pytest

from apoio import config, correli, correlt, gevazp_out, mes_estocastico, probvaz
from pulsar import oraculos as O


def _afetadas_por_nw(nome):
    """NINT das usinas NW e das usinas imediatamente a jusante delas."""
    cfg = config(nome)
    por_num = {u.num: u for u in cfg}
    out = set()
    for u in cfg:
        if u.status == "NW":
            out.add(u.nint)
            if u.jusante in por_num:
                out.add(por_num[u.jusante].nint)
    return out


def _confere(c, series, nome, excluir):
    p = probvaz(nome).astype(np.float64)
    mes = mes_estocastico(nome)
    n = 0
    for i in c.indice:
        if i in excluir:
            continue
        x = series.usina(i)
        s = c.serie(i)
        mu = p @ x
        assert abs(s.media_gerada[mes - 1] - mu) <= 1e-10 * max(1.0, abs(mu)), i
        sd = np.sqrt(p @ (x * x) - mu * mu)
        assert abs(s.desvio_gerado[mes - 1] - sd) <= 1e-8 * max(1.0, sd), i
        n += 1
    return n


def test_media_e_desvio_gerados_sao_ponderados_pelas_probabilidades(pacote):
    """INFERIDO F2-REL-01: media_gerada = Σ p x e desvio_gerado =
    sqrt(Σ p x² - média²), com p = PROBVAZ.DAT em float32."""
    excl = _afetadas_por_nw(pacote.nome) | {u.nint for u in config(pacote.nome) if u.status in ("PL",)}
    excl |= {u.nint for u in config(pacote.nome) if u.nome == "SOBRADINHO"}
    n = _confere(correli(pacote.nome), gevazp_out(pacote.nome), pacote.nome, excl)
    assert n >= 145
    t = O.ler_totais_gerados(pacote.arq("VAZTOTGD.DAT"))
    assert _confere(correlt(pacote.nome), t, pacote.nome, set()) == len(config(pacote.nome))


def test_nw_somada_na_jusante(pacote):
    """INFERIDO F2-REL-02: no GEVAZP.OUT a coluna da usina NW é nula e a sua
    incremental entra na usina de jusante; o correli guarda as duas séries
    separadas (médias geradas somam a média ponderada da coluna de jusante)."""
    cfg = config(pacote.nome)
    por_num = {u.num: u for u in cfg}
    c = correli(pacote.nome)
    g = gevazp_out(pacote.nome)
    p = probvaz(pacote.nome).astype(np.float64)
    mes = mes_estocastico(pacote.nome)
    nws = [u for u in cfg if u.status == "NW"]
    if not nws:
        pytest.skip("configuração sem usina NW")
    for u in nws:
        jus = por_num[u.jusante]
        assert not g.usina(u.nint).any()
        soma = c.serie(u.nint).media_gerada[mes - 1] + c.serie(jus.nint).media_gerada[mes - 1]
        assert abs(soma - p @ g.usina(jus.nint)) <= 1e-9 * soma, (u.nome, jus.nome)
