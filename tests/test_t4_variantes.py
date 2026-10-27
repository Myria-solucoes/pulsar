"""Poder de discriminação no T4: variantes descartadas dos resíduos, a
separação do coeficiente combinado que leva à ordem 0 e a folga entre a
FACP e o limiar de significância.

Proveniência: P-RES-01..03, P-NEG-03, P-ORD-02, P-ORD-03.
"""

import math

import numpy as np
import pytest

from apoio_parp import ajustes, confere_3_algarismos, residuos, residuos_rel
from pulsar import parp


def _frac(v):
    assert v
    return sum(v) / len(v)


def test_residuo_com_a_nula_no_primeiro_ano_erra(pacote):
    """P-RES-01: usar A = 0 (em vez de omitir o termo anual) no 1º ano erra
    mais de 100% em algum resíduo; a escolhida confere com 3 algarismos."""
    if not ajustes(pacote.nome) or not next(iter(ajustes(pacote.nome).values())).opcoes.anual:
        pytest.skip("variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02")
    rel = residuos_rel(pacote.nome)
    pior = 0.0
    for nome, aj in ajustes(pacote.nome).items():
        r = residuos(pacote.nome)[nome]
        ref = rel[nome].serie[aj.serie.anos[0]]
        z, an, est = aj.serie.valores, aj.anual, aj.est
        for m, md in enumerate(aj.modelos):
            if not r.validos[0, m] or md.ordem == 0:
                continue
            alt = r.valores[0, m] - md.psi * (0.0 - an.media[m]) / an.desvio[m]
            assert confere_3_algarismos(r.valores[0, m], ref[m])
            if ref[m] != 0:
                pior = max(pior, abs(alt - ref[m]) / abs(ref[m]))
    assert pior > 1.0


def _momentos(c):
    k = len(c)
    mm = parp.soma(c) / k
    ss = math.sqrt(parp.soma((v - mm) * (v - mm) for v in c) / k)
    g = k / ((k - 1) * (k - 2)) * parp.soma(((v - mm) / ss) ** 3 for v in c)
    return mm, ss, g


def test_momentos_contando_os_zeros_do_primeiro_ano_nao_batem(pacote):
    """P-RES-02: com os zeros do 1º ano, no máximo um terço das séries confere
    com o REL em cada momento (desvio e assimetria; a média só onde o REL não
    imprime zero de arredondamento)."""
    rel = residuos_rel(pacote.nome)
    ok = {"media": [], "desvio": [], "assimetria": []}
    for nome, r in residuos(pacote.nome).items():
        ref = rel[nome]
        mom = np.array([_momentos(r.valores[:, m].tolist()) for m in range(12)])
        cruza = ~r.validos[0]
        if not cruza.any():
            continue
        grande = np.abs(ref.media) > 1e-10
        ok["media"].append(bool(confere_3_algarismos(mom[grande, 0], ref.media[grande]).all()))
        ok["desvio"].append(bool(confere_3_algarismos(mom[:, 1], ref.desvio).all()))
        ok["assimetria"].append(bool(confere_3_algarismos(mom[:, 2], ref.assimetria).all()))
    for k, v in ok.items():
        assert _frac(v) < 1 / 3, k


def test_correlograma_dos_ruidos_variantes(pacote):
    """P-RES-03: só pares existentes (divisor N, nº de pares ou nº de resíduos
    do mês): no máximo 5% das séries conferem com as 5 casas do REL."""
    rel = residuos_rel(pacote.nome)
    ok = {"N": [], "pares": [], "n_mes": []}
    for nome, r in residuos(pacote.nome).items():
        ref = rel[nome].fac
        n = r.valores.shape[0]
        x = r.valores.reshape(-1)
        v = r.validos.reshape(-1)
        F = {k: np.zeros((11, 12)) for k in ok}
        for k in range(1, 12):
            for m in range(12):
                mk = (m - k) % 12
                p = [(x[t] - r.media[m]) * (x[t - k] - r.media[mk])
                     for t in range(m, x.size, 12) if t - k >= 0 and v[t] and v[t - k]]
                s = parp.soma(p) / (r.desvio[m] * r.desvio[mk])
                F["N"][k - 1, m] = s / n
                F["pares"][k - 1, m] = s / len(p)
                F["n_mes"][k - 1, m] = s / int(r.validos[:, m].sum())
        for k in ok:
            ok[k].append(bool(np.all(np.abs(F[k] - ref) <= 0.5e-5 + 1e-12)))
    for k, v in ok.items():
        assert _frac(v) <= 0.05, k


def test_separacao_do_coeficiente_combinado(pacote):
    """P-NEG-03: em todas as iterações, o combinado φ'_1 + ψ'/12 do ajuste de
    ordem 1 é ≤ -0,004 nos meses que vão a ordem 0 e ≥ 0,029 nos que ficam
    em ordem 1. ρ_1 dos dois grupos se sobrepõe. O sinal da FACP_1 não separa
    (há meses que ficam em ordem 1 com FACP_1 < 0); a FACP_1 só separaria nos
    pacotes com um limiar ad hoc entre -0,042 e -0,032, sem apoio em fonte."""
    if not ajustes(pacote.nome) or not next(iter(ajustes(pacote.nome).values())).opcoes.anual:
        pytest.skip("variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02")
    zero, um, facp_um, rho_zero, rho_um = [], [], [], [], []
    for aj in ajustes(pacote.nome).values():
        for it in aj.iteracoes:
            for m in range(12):
                if it.identificadas[m] != 1:
                    continue
                phi, psi = parp.yule_walker(aj.est, aj.anual, m, 1)
                c = phi[0] * aj.est.desvio[m] / aj.est.desvio[(m - 1) % 12] + psi * aj.est.desvio[m] / aj.anual.desvio[m] / 12
                (zero if it.modelos[m].ordem == 0 else um).append(c)
                (rho_zero if it.modelos[m].ordem == 0 else rho_um).append(aj.est.fac[1, m])
                if it.modelos[m].ordem == 1:
                    facp_um.append(aj.facp[0, m])
    assert zero and um
    assert max(zero) < 0 <= min(um)
    if pacote.nome in ("202609", "202610"):
        assert max(zero) <= -0.004 and min(um) >= 0.029
        assert min(facp_um) < 0  # o sinal da FACP de lag 1 não separa
        assert max(rho_zero) > min(rho_um)  # ρ_1 dos dois grupos se sobrepõe


def test_folga_do_limiar(pacote):
    """P-ORD-02: a menor folga entre |FACP| e 1,96/√N é positiva (nenhum
    empate, então `>` e `≥` não se distinguem); no 2026 fica entre 5e-6 e
    1e-5. Com 1,959964 as ordens identificadas (que o rastro do vordem.out
    confirma com 1,96) mudam só nos pacotes de 2024 (janela 1931–2022), em
    uma série; nos demais as duas constantes dão as mesmas ordens."""
    folgas = []
    muda = 0
    for aj in ajustes(pacote.nome).values():
        folgas.append(np.abs(np.abs(aj.facp) - aj.limiar).min())
        lim2 = parp.limiar_significancia(aj.est.n_anos, 1.959964)
        corta = aj.opcoes.facp_maior_que_1  # P-ORD-04
        for m in range(12):
            for it in aj.iteracoes:
                muda += parp.identificar(aj.facp[:, m], it.limites[m], lim2, aj.opcoes.ordem_minima, corta) \
                    != it.identificadas[m]
    assert min(folgas) > 0
    janela = next(iter(ajustes(pacote.nome).values())).serie.anos
    assert (muda > 0) == (janela[-1] == 2022), muda
    if pacote.nome in ("202609", "202610"):
        assert 5e-6 < min(folgas) < 1e-5


def test_sem_lag_significativo_a_ordem_e_1(pacote):
    """P-ORD-03: há casos (série, iteração, mês) sem nenhum lag significativo
    até o limite, e neles a ordem identificada é 1."""
    n = 0
    for aj in ajustes(pacote.nome).values():
        for it in aj.iteracoes:
            for m in range(12):
                lim = parp.limite_valido(aj.facp[:, m], it.limites[m])  # P-ORD-04
                if lim and not np.any(np.abs(aj.facp[:lim, m]) > aj.limiar):
                    assert it.identificadas[m] == 1
                    n += 1
    assert n > 0
