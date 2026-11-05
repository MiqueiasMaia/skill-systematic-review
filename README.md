# systematic-review-screening

Procedimento completo da etapa de triagem de uma revisão sistemática — da
concordância entre revisores ao diagrama de fluxo PRISMA 2020 — escrito como
*skill* para Claude Science, mas utilizável de forma independente: o
`SKILL.md` é um guia metodológico em Markdown e os dois scripts rodam com
Python puro.

Nasceu de uma revisão real sobre modelos de aprendizado de máquina na
recuperação de membro superior pós-AVC. Cada armadilha documentada aqui
custou tempo de verdade.

## Conteúdo

| Arquivo | O que é |
|---|---|
| `SKILL.md` | Guia das cinco etapas (concordância, adjudicação, consolidação, texto completo, PRISMA) e a lista de erros que não levantam exceção |
| `scripts/make_screening_tool.py` | Gera uma ferramenta HTML de avaliação de texto completo, com critérios de elegibilidade em cascata, campo de evidência verbatim e exportação CSV/JSON |
| `scripts/prisma_figure.py` | Gera o diagrama PRISMA 2020 a partir de um JSON de contagens, verificando a aritmética da cadeia antes de desenhar |

## Uso

Ferramenta de triagem de texto completo:

```bash
python scripts/make_screening_tool.py \
    --records records.csv \
    --pdf-dir pdf \
    --gates gates.json \
    --out 03-fulltext-screening.html
```

`records.csv` precisa ao menos de `id` e `title` (`doi` e `year` são
opcionais). `gates.json` é uma lista de `[código, nome, descrição]` na ordem
de avaliação — do critério mais barato de verificar ao mais caro. Os PDFs são
casados por título normalizado; o HTML deve ficar na pasta que contém
`--pdf-dir`, porque os links são relativos. As decisões ficam em
`localStorage` do navegador e saem por CSV ou JSON.

Diagrama PRISMA:

```bash
python scripts/prisma_figure.py prisma_counts.json --out prisma_flow
```

O esquema do JSON está documentado no cabeçalho do script. A cadeia é
verificada com `assert` antes do desenho: qualquer reclassificação que quebre
a aritmética falha ali, em vez de produzir silenciosamente uma figura
divergente do texto do manuscrito.

Requisitos: Python 3.9+ e `matplotlib` (só para a figura).

## Como skill do Claude Science

Coloque a pasta em `~/.cs/orgs/<org>/skills/` ou publique pelo
`host.skills.*`. O `SKILL.md` já traz o *frontmatter* com `name` e
`description`.
