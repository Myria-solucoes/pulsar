"""Geração dos cenários do período estocástico (02 §8–10; R1416 cap. 4).

Cadeia (R1416 cap. 4; R3383 Figura 2.4; L-RUID):

1. amostra original de ruídos normais independentes, uma coluna por posto
   (``ruidos``), agregada por K-means com K = aberturas do período
   estocástico, centroide como representante e fator de compensação
   (``agregacao``);
2. correlação espacial ``W = D b`` com a matriz de carga da F4
   (``pulsar.espacial``; M18 eq. 4.16);
3. ruído dos postos laterais condicionado aos principais (M18 eq. 4.19–4.20);
4. lognormal de três parâmetros (``lognormal``) e recorrência PAR(p)-A com
   a tendência hidrológica da F5 (M18 eq. 4.9a);
5. totalização, postos artificiais e incrementais recalculadas pela F6
   (``pulsar.totalizacao``), que dão GEVAZP.OUT, VAZTOTGD.DAT, vazoesta.out e
   vazoesia.out, e probabilidades contagem/N para o PROBVAZ.DAT (F7).

Proveniência: P-GER-01..09, P-LAT-01..03, P-AGR-*, P-LN3-* em PROVENIENCIA.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

from .. import espacial, historico, parp
from ..configuracao import LATERAL, NULO, Configuracao, montar_configuracao
from ..empacotamento.probvaz import gravar_probvaz, probabilidades_de_contagens
from ..tendencia import tendencia
from ..totalizacao import SeriesTotalizadas, calcular_series, dados_defasagem, gravar_series, mes_e_ano_estocastico
from .agregacao import Agregacao, OpcoesAgregacao, agregar, compensar
from .lognormal import MOMENTOS, ROTAS, ParametrosLN3, limite_por_quantis, parametros

MESES = 12
# P-GER-01 (ESCOLHA, lacuna L6): semente padrão (configurável).
SEMENTE_PADRAO = 0
CORRELACOES_LATERAL = ("anual", "mensal")


class ErroGeracao(ValueError):
    pass


@dataclass(frozen=True)
class OpcoesGeracao:
    semente: int = SEMENTE_PADRAO
    agregacao: OpcoesAgregacao = field(default_factory=OpcoesAgregacao)
    # P-LN3-03 (lacuna L8): rota do limite inferior da lognormal.
    rota_limite: str = "zero"
    # P-LN3-04: momentos do ruído (teóricos: μ_a = 0, σ_a² = 1 - Σφρ - ψρ_A).
    momentos: str = "teoricos"
    # P-LN3-06: μ_a - Δ ≤ 0.
    sem_lognormal: str = "quadrado"
    # P-LAT-02 (DOC M18 eq. 4.19: correlações anuais; variante "mensal").
    correlacao_lateral: str = "anual"
    # Parâmetros da F4 (P-ESP-05, P-ESP-07, P-ESP-08).
    laterais_na_carga: str = "fora"
    nao_positivos: str = "zero"
    soma_produto: str = "numpy"

    def __post_init__(self):
        if self.rota_limite not in ROTAS:
            raise ValueError(self.rota_limite)
        if self.momentos not in MOMENTOS:
            raise ValueError(self.momentos)
        if self.correlacao_lateral not in CORRELACOES_LATERAL:
            raise ValueError(self.correlacao_lateral)


@dataclass(frozen=True)
class SerieGerada:
    indice: int  # posição na configuração completa
    numero: int
    nome: str
    posto: int
    passado: np.ndarray  # Z_{t-j}, j = 1..12
    anual: float  # A_{t-1}
    c: float  # termo condicional: Z_t = σ_m (c + a_t)
    ln3: ParametrosLN3
    w: np.ndarray  # [K] ruído normal correlacionado
    z: np.ndarray  # [K] incremental gerada


@dataclass(frozen=True)
class Resultado:
    mes: int  # mês do calendário do período estocástico
    ano_estudo: int
    agregacao: Agregacao
    series: list[SerieGerada]
    incrementais_geradas: np.ndarray  # [K, usinas da configuração completa]
    totalizadas: SeriesTotalizadas
    probabilidades: np.ndarray  # float32, contagem/N (F7-PB-02)


# --------------------------------------------------------------------------
# Passado e termo condicional


def passado_da_serie(tend, posto: int, mes: int) -> tuple[np.ndarray, float]:
    """P-GER-03: Z_{t-j} (j = 1..12) = incremental do QPAST (F5, P-TEND-05)
    no mês do calendário ``mes - j``; A_{t-1} = soma sequencial dos 12 meses
    na ordem do calendário (jan..dez) / 12 (F2-VA-03)."""
    inc = tend.incremental[:, posto - 1]
    z = np.array([inc[(mes - 1 - j) % MESES] for j in range(1, MESES + 1)])
    s = 0.0
    for m in range(MESES):
        s += inc[m]
    return z, s / MESES


def termo_condicional(aj: parp.AjustePAR, m: int, zpass, a_ant: float) -> float:
    """P-GER-04: c = μ_m/σ_m + Σ_i φ_i (Z_{t-i} - μ_{m-i})/σ_{m-i}
    + ψ (A_{t-1} - μ^A_m)/σ^A_m, mês m (0..11) do período; o termo anual só
    com ordem ≥ 1 (P-RES-01). Z_t = σ_m (c + a_t) é a recorrência da M18
    eq. 4.9a (L-LN3 eq. 18). INFERIDO: σ_m c = "MEDIA TEO" do TCOND.REL."""
    est, md = aj.est, aj.modelos[m]
    c = est.media[m] / est.desvio[m]
    for i in range(1, md.ordem + 1):
        mi = (m - i) % MESES
        c += md.phi[i - 1] * (zpass[i - 1] - est.media[mi]) / est.desvio[mi]
    if aj.anual is not None and md.ordem:
        c += md.psi * (a_ant - aj.anual.media[m]) / aj.anual.desvio[m]
    return c


def momentos_do_ruido(aj: parp.AjustePAR, m: int, momentos: str, res: parp.Residuos | None = None) -> tuple[float, float]:
    """P-LN3-04: "teoricos" = (0, √(1 - Σ φ_i ρ_i^m - ψ ρ_{Z,A}(0)^m)) (M18 eq.
    4.8, 4.9b e 6.11; R1416 eq. 16); "historicos" = média e desvio dos
    resíduos históricos do mês (P-RES-02; L-LN3, "momentos dos resíduos")."""
    if momentos == "historicos":
        r = res or parp.residuos(aj)
        return float(r.media[m]), float(r.desvio[m])
    md = aj.modelos[m]
    v = 1.0
    for i in range(1, md.ordem + 1):
        v -= md.phi[i - 1] * aj.est.fac[i, m]
    if aj.anual is not None and md.ordem:
        v -= md.psi * aj.anual.correlacao[0, m]
    if not v > 0:
        raise ErroGeracao(f"{aj.serie.nome}: variância teórica do ruído {v!r} não positiva no mês {m + 1}")
    return 0.0, float(np.sqrt(v))


# --------------------------------------------------------------------------
# Laterais (lacuna L11)


def condicional_lateral(sigma12: np.ndarray, sigma22: np.ndarray) -> tuple[np.ndarray, float]:
    """M18 eq. 4.19–4.20 (L-VIAG eq. 55–56): W1 = (Σ12 Σ22⁻¹) W2 + E b1,
    E E' = 1 - Σ12 Σ22⁻¹ Σ12'. Devolve (Σ12 Σ22⁻¹, E)."""
    g = np.linalg.solve(np.atleast_2d(sigma22), np.atleast_1d(sigma12))
    e2 = 1.0 - float(np.atleast_1d(sigma12) @ g)
    if e2 < 0:
        raise ErroGeracao(f"variância condicional do lateral {e2!r} negativa")
    return g, float(np.sqrt(e2))


# --------------------------------------------------------------------------
# Cadeia completa


@dataclass
class Preparo:
    """Tudo o que a geração usa e que não depende da semente."""

    cfg: Configuracao
    k: int  # aberturas do período estocástico
    mes: int
    ano_estudo: int
    todas: list  # séries incrementais (sem as PN), na ordem da configuração
    indice: dict  # id(série) -> posição na configuração completa
    ajustes: dict  # id(série) -> AjustePAR
    carga: list  # séries da matriz de carga
    d: np.ndarray  # matriz de carga
    laterais: list  # postos laterais fora da carga
    cond: dict  # id(lateral) -> (índices dos principais na carga, Σ12 Σ22⁻¹, E)

    @property
    def postos(self) -> list[int]:
        """P-AGR-07: componentes do vetor agregado = séries da carga, depois
        um ruído próprio por posto lateral, cada um com a chave do seu posto."""
        return [s.posto for s in self.carga] + [s.posto for s in self.laterais]


def preparar(deck, cfg: Configuracao | None = None, opcoes: OpcoesGeracao | None = None,
             ajustes: list[parp.AjustePAR] | None = None) -> Preparo:
    op = opcoes or OpcoesGeracao()
    cfg = cfg or montar_configuracao(deck)
    v = deck.dadger.vazoes
    if len(v.aberturas) != 1:
        # P-GER-02: só um período estocástico (F2-ARV-03, F2-VZ-09, F7-VZ-02).
        raise NotImplementedError(f"aberturas {v.aberturas}: só um período estocástico é suportado")
    mes, ano_estudo = mes_e_ano_estocastico(v.mes_inicial)

    # Séries, ajustes (F3) e índices na configuração completa.
    todas = historico.series_incrementais(deck.historico, cfg)
    pos = [i for i, u in enumerate(cfg.completa) if u.status != NULO]
    indice = {id(s): i for s, i in zip(todas, pos, strict=True)}
    if ajustes is None:
        opp = parp.opcoes_do_deck(deck)
        ajustes = [parp.ajustar(s, opp) for s in historico.series_ajustadas(todas, v.ajuste_todas)]
    por_chave = {(aj.serie.numero, aj.serie.status == LATERAL): aj for aj in ajustes}
    aj_por = {id(s): por_chave[(s.numero, s.status == LATERAL)] for s in todas if not s.nula}

    # Matriz de carga (F4), P-GER-08.
    carga = espacial.series_da_carga(todas, op.laterais_na_carga)
    corr_carga = espacial.correlacao_espacial(carga)
    u = espacial.matriz_do_estudo(corr_carga, mes, v.matriz_mensal)
    d = espacial.matriz_de_carga(u, corr_carga.numeros, op.nao_positivos, soma_produto=op.soma_produto).d

    # Laterais fora da carga: ruído próprio, condicionado ao principal
    # (P-LAT-01..03).
    na_carga = {id(t): j for j, t in enumerate(carga)}
    laterais = [s for s in todas if s.status == LATERAL and not s.nula and id(s) not in na_carga]
    cond = {}
    for s in laterais:
        ul = cfg.completa[indice[id(s)]]
        principal = [t for t in carga if t.status != LATERAL and t.numero == ul.origem_lateral]
        if len(principal) != 1:
            raise ErroGeracao(f"{s.nome}: posto total {ul.origem_lateral} sem série na matriz de carga")
        cl = espacial.correlacao_espacial([s] + principal)
        mat = cl.anual if op.correlacao_lateral == "anual" else cl.mes(mes)
        g, e = condicional_lateral(mat[0, 1:], mat[1:, 1:])
        cond[id(s)] = ([na_carga[id(t)] for t in principal], g, e)
    return Preparo(cfg, v.aberturas[0], mes, ano_estudo, todas, indice, aj_por, carga, d, laterais, cond)


def gerar(deck, cfg: Configuracao | None = None, opcoes: OpcoesGeracao | None = None,
          ajustes: list[parp.AjustePAR] | None = None, agregacao: Agregacao | None = None,
          preparo: Preparo | None = None) -> Resultado:
    """Cenários do período estocástico do deck. ``ajustes``, ``preparo`` e
    ``agregacao`` reaproveitam um ajuste (F3), um preparo ou uma agregação
    já feitos (a agregação com a mesma semente e simetria; o fator de
    compensação é refeito pela variante de ``opcoes``)."""
    op = opcoes or OpcoesGeracao()
    pr = preparo or preparar(deck, cfg, op, ajustes)
    cfg, k, mes, m = pr.cfg, pr.k, pr.mes, pr.mes - 1

    # Ruídos agregados (P-AGR-*).
    if agregacao is None:
        ag = agregar(pr.postos, k, op.semente, op.agregacao)
    else:
        if agregacao.postos != tuple(pr.postos) or agregacao.contagens.size != k:
            raise ErroGeracao("agregação reaproveitada com outros postos ou outro número de aberturas")
        ag = compensar(agregacao, op.agregacao.desvio, op.agregacao.aplicacao)

    # Correlação espacial W = D b (M18 eq. 4.16) e laterais (eq. 4.19).
    b = ag.ruidos
    n = len(pr.carga)
    w_carga = b[:, :n] @ pr.d.T
    w = {id(s): w_carga[:, j] for j, s in enumerate(pr.carga)}
    for j, s in enumerate(pr.laterais):
        idx, g, e = pr.cond[id(s)]
        w[id(s)] = w_carga[:, idx] @ g + e * b[:, n + j]

    # Lognormal e recorrência (F5: tendência).
    tend = tendencia(deck, cfg)
    inc = np.zeros((k, len(cfg.completa)))
    geradas = []
    for s in pr.todas:
        if s.nula:
            continue  # P-GER-09: incremental nula fica 0
        aj = pr.ajustes[id(s)]
        zp, a_ant = passado_da_serie(tend, s.posto, mes)
        c = termo_condicional(aj, m, zp, a_ant)
        mu_a, sd_a = momentos_do_ruido(aj, m, op.momentos)
        gama = lim = None
        if op.rota_limite == "cubica_residuos":
            gama = float(parp.residuos(aj).assimetria[m])
        elif op.rota_limite == "cubica_vazoes":
            gama = float(aj.est.assimetria[m])
        elif op.rota_limite == "quantis":
            lim = limite_por_quantis(s.valores[:, m])
        sig = float(aj.est.desvio[m])
        ln3 = parametros(c, sig, mu_a, sd_a, op.rota_limite, gama, lim, op.sem_lognormal)
        a_t = ln3.ruido(w[id(s)])
        z = recorrencia(aj, m, zp, a_ant, a_t)
        i = pr.indice[id(s)]
        inc[:, i] = z
        geradas.append(SerieGerada(i, s.numero, s.nome, s.posto, zp, a_ant, c, ln3, w[id(s)], z))

    defas = dados_defasagem(deck, cfg) if any(x.posto_lateral and x.defasagem == 2 for x in cfg.usinas) else None
    tot = calcular_series(inc, cfg, deck.regras, mes, pr.ano_estudo, defas)
    prob = probabilidades_de_contagens(ag.contagens, ag.n_objetos)
    return Resultado(mes, pr.ano_estudo, ag, geradas, inc, tot, prob)


def recorrencia(aj: parp.AjustePAR, m: int, zpass, a_ant: float, a_t: np.ndarray) -> np.ndarray:
    """P-GER-05: Z_t = μ_m + Σ_i φ_i σ_m (Z_{t-i} - μ_{m-i})/σ_{m-i}
    + ψ σ_m (A_{t-1} - μ^A_m)/σ^A_m + σ_m a_t (M18 eq. 4.9a; L-PARA eq. 31;
    termo anual só com ordem ≥ 1, P-RES-01), somado nessa ordem."""
    est, md = aj.est, aj.modelos[m]
    sm = est.desvio[m]
    z = est.media[m]
    for i in range(1, md.ordem + 1):
        mi = (m - i) % MESES
        z = z + md.phi[i - 1] * sm * (zpass[i - 1] - est.media[mi]) / est.desvio[mi]
    if aj.anual is not None and md.ordem:
        z = z + md.psi * sm * (a_ant - aj.anual.media[m]) / aj.anual.desvio[m]
    return z + sm * np.asarray(a_t)


def montar_vazoes(deck, cfg: Configuracao, resultado: Resultado, npos: int | None = None, opcoes=None):
    """P-GER-07: entrega à F7: ``ArvoreVazoes`` do VAZOES.RVx com os blocos
    gerados (GEVAZP.OUT e vazoesia.out desta geração), as probabilidades
    (PROBVAZ.DAT) e os registros determinísticos da F5."""
    from ..empacotamento.vazoes_rvx import RegistrosDeterministicos, montar_arvore
    from ..vazoes_deterministicos import montar_registros

    r = montar_registros(deck, cfg)
    det = RegistrosDeterministicos(r.prevista_semanal, r.prevista_semanal_ena, r.observada_mensal, r.observada_semanal)
    t = resultado.totalizadas
    return montar_arvore(cfg, deck.dadger.vazoes, deck.n_postos, t.incrementais, t.incrementais_artificiais,
                         resultado.probabilidades, det, npos or deck.n_postos, opcoes)


def gravar(diretorio, resultado: Resultado, npos: int) -> None:
    """P-GER-06: GEVAZP.OUT, VAZTOTGD.DAT, vazoesta.out e vazoesia.out
    (F6-GRV-01, U19 §5.3.1.2) e PROBVAZ.DAT (F7-PB-01, U19 §5.4)."""
    os.makedirs(diretorio, exist_ok=True)
    gravar_series(diretorio, resultado.totalizadas, npos)
    gravar_probvaz(os.path.join(diretorio, "PROBVAZ.DAT"), resultado.probabilidades, npos)
