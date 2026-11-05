#!/usr/bin/env python3
"""Diagrama de fluxo PRISMA 2020 a partir de um JSON de contagens.

Uso:
    python prisma_figure.py prisma_counts.json --out prisma_flow

Esquema esperado do JSON (chaves obrigatorias):
    identified            int    registros identificados nas bases
    duplicates_removed    int
    screened              int    triados por titulo e resumo
    excluded_screening    int
    assessed_fulltext     int    relatorios buscados e avaliados
    excluded_fulltext     int
    exclusion_reasons     dict   motivo -> n  (soma = excluded_fulltext)
    included              int    estudos incluidos na sintese
    sources               dict   opcional: base -> n (soma = identified)

A cadeia e verificada com assert antes de desenhar: qualquer
reclassificacao que quebre a aritmetica falha aqui, em vez de produzir
silenciosamente uma figura divergente do texto.

Terminologia PRISMA 2020: 'records' ate a triagem, 'reports' na etapa de
texto completo, 'studies' so na caixa final.
"""
import argparse, json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

MX, MW, BH = 8, 48, 9          # coluna principal: x, largura, altura
SX, SW = 60, 34                # coluna lateral
Y_MAIN = [86, 66, 46, 26]      # base das caixas principais
Y_SIDE = [77.5, 57.5, 35.5]    # base das caixas laterais
EDGE = "#333333"


def box(ax, x, y, w, h, text, fontsize=8):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white",
                           edgecolor=EDGE, linewidth=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, linespacing=1.4)


def arrow(ax, x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=EDGE,
                                linewidth=0.8, shrinkA=0, shrinkB=0))


def band(ax, y, h, label):
    ax.add_patch(Rectangle((1, y), 5, h, facecolor="#E8ECEF", edgecolor="none"))
    ax.text(3.5, y + h / 2, label, rotation=90, ha="center", va="center",
            fontsize=8, color=EDGE)


def check(P):
    assert P["identified"] - P["duplicates_removed"] == P["screened"], "cadeia: identificados"
    assert P["screened"] - P["excluded_screening"] == P["assessed_fulltext"], "cadeia: triagem"
    assert P["assessed_fulltext"] - P["excluded_fulltext"] == P["included"], "cadeia: texto completo"
    assert sum(P["exclusion_reasons"].values()) == P["excluded_fulltext"], "motivos nao somam"
    if P.get("sources"):
        assert sum(P["sources"].values()) == P["identified"], "bases nao somam"


def build(P):
    fig, ax = plt.subplots(figsize=(7.0, 7.0), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(Y_MAIN[3] - 4, Y_MAIN[0] + BH + 4)
    ax.axis("off")

    y_id, y_scr, y_elg, y_inc = Y_MAIN
    y_dup, y_ex1, y_ex2 = Y_SIDE

    box(ax, MX, y_id, MW, BH, "Records identified from databases\n(n = %d)" % P["identified"])
    box(ax, MX, y_scr, MW, BH, "Records screened\n(n = %d)" % P["screened"])
    box(ax, MX, y_elg, MW, BH, "Reports assessed for eligibility\n(n = %d)" % P["assessed_fulltext"])
    box(ax, MX, y_inc, MW, BH, "Studies included in review\n(n = %d)" % P["included"])

    box(ax, SX, y_dup, SW, 6, "Duplicate records removed\n(n = %d)" % P["duplicates_removed"])
    box(ax, SX, y_ex1, SW, 6, "Records excluded\n(n = %d)" % P["excluded_screening"])
    reasons = "\n".join("%s: n = %d" % (k, v) for k, v in P["exclusion_reasons"].items())
    box(ax, SX, y_ex2, SW, 10,
        "Reports excluded (n = %d)\n%s" % (P["excluded_fulltext"], reasons), fontsize=7)

    cx = MX + MW / 2
    for y_from, y_to in zip(Y_MAIN[:-1], Y_MAIN[1:]):
        arrow(ax, cx, y_from, cx, y_to + BH)
    for y in Y_SIDE:
        mid = y + 3 if y != y_ex2 else y + 5
        arrow(ax, cx, mid, SX, mid)

    band(ax, y_dup, (y_id + BH) - y_dup, "Identification")
    band(ax, y_ex2, (y_scr + BH) - y_ex2, "Screening")
    band(ax, y_inc, BH, "Included")
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("counts")
    ap.add_argument("--out", default="prisma_flow")
    a = ap.parse_args()
    P = json.load(open(a.counts, encoding="utf-8"))
    check(P)
    fig = build(P)
    for ext in ("png", "pdf"):
        fig.savefig("%s.%s" % (a.out, ext), dpi=300, bbox_inches="tight", facecolor="white")
    print("escrito: %s.png, %s.pdf" % (a.out, a.out))


if __name__ == "__main__":
    main()
