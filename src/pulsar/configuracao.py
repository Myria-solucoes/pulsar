"""Configuração final das usinas no modo DECOMP (U19 §3.4.1, §4.5, §4.6,
§4.11; 02 §2).

Cada usina tem os 14 campos do arquivo de configuração do U19 §3.4.1. A
configuração é montada a partir de DADGER (UH, AC, VI, bloco & VAZOES),
HIDR.DAT, MODIF.DAT, POSTOS.DAT e GEVAZP.DAT.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

from .entradas.deck import Deck
from .entradas.texto import ErroLeitura

# Status (U19 §3.4.1 campo 7; NW: nota secundária da versão 11 e DADGER).
EXISTENTE = "  "
NULO = "PN"
NAO_CONSIDERA = "NC"
NEWAVE = "NW"
LATERAL = "PL"

# P-CFG-13: defasagem linear quando o DADGER não informa o reg. 12
# (U19 §3.4.1 campo 13 e §4.5 reg. 12: default 2).
DEFASAGEM_PADRAO = 2


@dataclass
class UsinaConfig:
    """Os 14 campos do U19 §3.4.1 e as ligações derivadas."""

    numero: int
    nome: bytes  # A12 do HIDR (ou nome derivado para o posto lateral)
    posto: int
    jusante: int
    bacia: int
    # P-CFG-18: campos 6 e 8 sempre 0 no modo DECOMP (nenhuma entrada os
    # altera; o campo 8 independe do & VAZOES reg. 16).
    percentual_minimo: float = 0.0
    status: str = EXISTENTE
    ajuste_automatico: int = 0
    ano_inicial: int = 0
    ano_final: int = 0
    tempo_viagem: int = 0
    posto_lateral: int = 0
    defasagem: int = DEFASAGEM_PADRAO
    posto_artificial: int = 0
    # Derivados (não gravados): valor bruto do AC NPOSNW e usina de origem
    # do posto lateral.
    nposnw: int = 0
    origem_lateral: int | None = None

    @property
    def nome_str(self) -> str:
        return self.nome.decode("latin-1").rstrip()


@dataclass
class Configuracao:
    usinas: list[UsinaConfig]  # configuração base (bloco 1 do config.out)
    laterais: list[UsinaConfig] = field(default_factory=list)  # postos laterais (P-CFG-11)
    ano_inicial_comum: int = 0
    ano_final_comum: int = 0

    @property
    def completa(self) -> list[UsinaConfig]:
        """Base + postos laterais (bloco 2 do config.out)."""
        return self.usinas + self.laterais

    def por_numero(self) -> dict[int, UsinaConfig]:
        return {u.numero: u for u in self.usinas}

    def montante(self, numero: int) -> list[int]:
        """Usinas imediatamente a montante, na ordem da configuração."""
        return [u.numero for u in self.usinas if u.jusante == numero]

    def postos_montante(self, numero: int) -> list[int]:
        """Postos das usinas imediatamente a montante, na ordem da
        configuração (P-CFG-17, INFERIDO: REL "CONFIGURACAO UTILIZADA PELO
        DECOMP")."""
        por_num = self.por_numero()
        return [por_num[n].posto for n in self.montante(numero)]

    def ordem_vazoes_rv(self) -> list[int]:
        """Ordem das usinas no registro 2 do VAZOES.RVx.

        P-CFG-16 (INFERIDO): as usinas da configuração base sem ``NW``, na
        ordem da configuração, seguidas das ``NW`` na ordem da configuração.
        """
        return [u.numero for u in self.usinas if u.status != NEWAVE] + [
            u.numero for u in self.usinas if u.status == NEWAVE
        ]

    @property
    def postos_partif(self) -> list[int]:
        return [u.numero for u in self.usinas if u.status == NULO]


def nome_lateral(nome: bytes) -> bytes:
    """P-CFG-12: nome do posto lateral = nome da usina sem os brancos à
    direita + ``_L`` (INFERIDO, ``SOBRADINHO_L``), cortado em 12 caracteres
    quando passa disso (ESCOLHA, lacuna L13; trocável em
    ``OpcoesConfiguracao.nome_lateral``)."""
    base = nome.rstrip(b" \x00") + b"_L"
    return base[:12].ljust(12, b" ")


@dataclass(frozen=True)
class OpcoesConfiguracao:
    """Escolhas da configuração que os dados públicos não decidem.

    Os padrões reproduzem os config.out públicos (202609, 202610).
    """

    # P-CFG-08 (lacuna L1): "intersecao" = POSTOS.DAT limitado por
    # GEVAZP.DAT reg. 16 e & VAZOES reg. 2; "postos" = só POSTOS.DAT;
    # "geral" = só GEVAZP.DAT reg. 16 e & VAZOES reg. 2.
    anos: str = "intersecao"
    # P-CFG-06 (lacuna L14): status de usina NW e PARTIF ao mesmo tempo.
    prioridade_status: str = NEWAVE
    # P-CFG-11 (lacuna L14): ordem dos postos laterais no bloco 2:
    # "origem" (ordem das usinas de origem) ou "numero" (crescente do posto).
    ordem_laterais: str = "origem"
    # P-CFG-12 (lacuna L13).
    nome_lateral: Callable[[bytes], bytes] = nome_lateral
    # P-DADG-05 (lacuna L14): AC repetido, "ultimo" ou "primeiro".
    ac_repetido: str = "ultimo"
    # P-DADG-12 (lacuna L14): AC datado depois da 1ª semana do mês inicial
    # do estudo, "vale" ou "ignora".
    ac_datado_futuro: str = "vale"
    # P-DADG-13 (lacuna L14): ano ausente na data do AC, "estudo",
    # "proximo" ou "erro" (semana ausente vale 1).
    ac_ano_ausente: str = "estudo"

    def __post_init__(self):
        if self.anos not in ("intersecao", "postos", "geral"):
            raise ValueError(self.anos)
        if self.prioridade_status not in (NEWAVE, NULO):
            raise ValueError(self.prioridade_status)
        if self.ordem_laterais not in ("origem", "numero"):
            raise ValueError(self.ordem_laterais)


def montar_configuracao(deck: Deck, opcoes: OpcoesConfiguracao | None = None) -> Configuracao:
    op = opcoes or OpcoesConfiguracao()
    if deck.dadger is None or deck.hidr is None:
        raise ErroLeitura("configuração exige DADGER e HIDR")
    dg = deck.dadger
    v = dg.vazoes
    hidr = deck.hidr

    # P-CFG-01: usinas = registros UH do DADGER (U19 §4.5).
    # P-CFG-15 (INFERIDO): UH repetido conta uma vez, na primeira posição
    # (DADGER 202009 RV2 contra o vazoes.rv2 público).
    vistos: set[int] = set()
    uh = []
    for r in dg.uh:
        if r.usina in vistos:
            continue
        vistos.add(r.usina)
        uh.append(r)

    # P-CFG-02: ordenação crescente do número da usina quando o reg. 14 do
    # & VAZOES vale 1 (U19 §4.5); senão, ordem dos registros UH.
    if v is not None and v.ordenacao_automatica == 1:
        uh.sort(key=lambda r: r.usina)

    # P-DADG-12: início do estudo = (ano, mês) do & VAZOES reg. 4; sem o
    # ano no reg. 4, o reg. 6 (U19 §4.5 duplica o ano inicial nos dois);
    # sem mês ou ano, inicio = None e nenhum AC conta como posterior.
    inicio = None
    if v is not None and v.mes_inicial:
        ano_ini = v.ano_inicial or v.ano_inicial_estudo
        if ano_ini:
            inicio = (ano_ini, v.mes_inicial)

    def ac(mn: str) -> dict[int, int]:
        return dg.ac_config(mn, op.ac_repetido, inicio, op.ac_datado_futuro, op.ac_ano_ausente)

    numpos = ac("NUMPOS")
    numjus = ac("NUMJUS")
    nposnw = ac("NPOSNW")
    tv = {r.usina: r.duracao for r in dg.vi}
    partif = {m.usina for m in (deck.modif or []) if m.palavra == "PARTIF"}
    vincr = {m.usina: m for m in (deck.modif or []) if m.palavra == "VINCR"}

    defl = DEFASAGEM_PADRAO
    if v is not None and v.defasagem_linear:
        defl = v.defasagem_linear  # P-CFG-09: U19 §4.5 reg. 12

    ano_ini_geral = deck.gevazp.ano_inicial_historico if deck.gevazp else None
    ano_fim_geral = v.ano_final_historico if v is not None else None

    def anos(posto: int) -> tuple[int, int]:
        # P-CFG-08 (ESCOLHA, lacuna L1): anos do POSTOS.DAT (U19 §3.4.1:
        # sem anos no arquivo de configuração, vale o POSTOS.DAT), limitados
        # pelo ano inicial do GEVAZP.DAT (reg. 16) e pelo ano final do
        # histórico do DADGER (& VAZOES reg. 2); ver OpcoesConfiguracao.anos.
        ini, fim = (0, 0) if op.anos == "postos" else (ano_ini_geral or 0, ano_fim_geral or 0)
        if op.anos != "geral" and deck.postos is not None and posto in deck.postos:
            p = deck.postos[posto]
            if p.ano_inicial:
                ini = max(ini, p.ano_inicial) if ini else p.ano_inicial
            if p.ano_final:
                fim = min(fim, p.ano_final) if fim else p.ano_final
        return ini, fim

    usinas: list[UsinaConfig] = []
    for r in uh:
        h = hidr[r.usina]
        # P-CFG-03: posto do HIDR, substituído por AC NUMPOS.
        posto = numpos.get(r.usina, h.posto)
        # P-CFG-04: jusante do HIDR, substituída por AC NUMJUS.
        jus = numjus.get(r.usina, h.jusante)
        lateral = 0
        if r.usina in vincr:
            # P-CFG-10: VINCR usina, posto lateral, posto total (U19 §4.11):
            # o posto da usina passa a ser o total e o lateral vai ao campo 12.
            m = vincr[r.usina]
            lateral = m.campo3
            posto = m.campo4
        # P-CFG-06: NW (col. 72 do UH) e PARTIF (PN); a precedência quando
        # há os dois é OpcoesConfiguracao.prioridade_status.
        marcas = [s for s, tem in ((NEWAVE, r.nw), (NULO, r.usina in partif)) if tem]
        if len(marcas) == 2:
            status = op.prioridade_status
        else:
            status = marcas[0] if marcas else EXISTENTE
        ini, fim = anos(posto)
        usinas.append(
            UsinaConfig(
                numero=r.usina,
                nome=h.nome_bruto,
                posto=posto,
                jusante=jus,
                bacia=r.ree,  # P-CFG-05: bacia = REE do registro UH
                status=status,
                ano_inicial=ini,
                ano_final=fim,
                tempo_viagem=tv.get(r.usina, 0),  # P-CFG-07: VI do DADGER
                posto_lateral=lateral,
                defasagem=defl,
                # P-CFG-14: posto artificial = AC NPOSNW. Em usina com posto
                # lateral o NPOSNW indica o posto total (U19 §4.5) e não um
                # artificial: o campo fica 0 (INFERIDO numa só usina,
                # SOBRADINHO, a única com VINCR nos pacotes).
                posto_artificial=0 if lateral else nposnw.get(r.usina, 0),
                nposnw=nposnw.get(r.usina, 0),
            )
        )

    # P-CFG-04b (INFERIDO): jusante fora da configuração é substituída pela
    # primeira usina presente seguindo a cadeia de jusantes do cadastro
    # (HIDR, com AC NUMJUS); sem nenhuma, vira 0 (U19 §3.4.1).
    presentes = {u.numero for u in usinas}

    def jusante_cadastro(n: int) -> int:
        if n in numjus:
            return numjus[n]
        return hidr[n].jusante if n in hidr.usinas else 0

    for u in usinas:
        j = u.jusante
        visitados = {u.numero}
        while j and j not in presentes:
            if j in visitados:
                raise ErroLeitura(f"ciclo de jusantes a partir da usina {u.numero}")
            visitados.add(j)
            j = jusante_cadastro(j)
        u.jusante = j

    # P-CFG-11: cada posto lateral vira uma usina extra no fim (bloco 2).
    laterais = []
    origens = [u for u in usinas if u.posto_lateral]
    if op.ordem_laterais == "numero":
        origens.sort(key=lambda u: u.posto_lateral)
    for u in origens:
        if u.posto_lateral:
            ini, fim = anos(u.posto_lateral)
            laterais.append(
                replace(
                    u,
                    numero=u.posto_lateral,
                    nome=op.nome_lateral(u.nome),
                    posto=u.posto_lateral,
                    jusante=0,
                    percentual_minimo=0.0,
                    status=LATERAL,
                    ajuste_automatico=0,
                    ano_inicial=ini,
                    ano_final=fim,
                    tempo_viagem=0,
                    posto_lateral=0,
                    posto_artificial=0,
                    nposnw=0,
                    origem_lateral=u.numero,
                )
            )

    todos = usinas + laterais
    return Configuracao(
        usinas=usinas,
        laterais=laterais,
        ano_inicial_comum=max(u.ano_inicial for u in todos) if todos else 0,
        ano_final_comum=min(u.ano_final for u in todos) if todos else 0,
    )
