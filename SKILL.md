---
name: systematic-review-screening
description: "Triagem de revisao sistematica de ponta a ponta: concordancia entre revisores (kappa de Cohen, PABAK, indices de prevalencia e vies), adjudicacao de divergencias, consolidacao das decisoes com procedencia, avaliacao de texto completo com criterios de elegibilidade em cascata, e diagrama de fluxo PRISMA 2020 derivado dos dados. Use ao calcular concordancia entre dois triadores, ao consolidar decisoes de triagem, ao montar ferramenta de avaliacao de texto completo, ou ao fechar o fluxo PRISMA."
---

# Triagem de revisao sistematica

Procedimento completo da triagem, da concordancia entre revisores ao diagrama
PRISMA. Escrito a partir de uma revisao real; cada armadilha listada aqui
custou tempo de verdade.

## Ordem das etapas, e por que ela nao pode mudar

1. **Concordancia** sobre as decisoes brutas e independentes dos dois revisores.
2. **Adjudicacao** das divergencias.
3. **Consolidacao** de uma decisao final por registro.
4. **Texto completo** sobre os registros aprovados.
5. **PRISMA** derivado dos arquivos das etapas anteriores.

O kappa vem **antes** da adjudicacao, sempre. Ele mede convergencia entre
avaliadores trabalhando de forma independente; depois da adjudicacao a
concordancia e 1 por construcao e o numero nao mede nada. A adjudicacao
alimenta o fluxo PRISMA, nao a estatistica de concordancia.

## 1. Pareamento e normalizacao

```python
d = A[["id", "decision"]].merge(B[["id", "decision"]], on="id",
                                suffixes=("_a", "_b"))
assert len(d) == N_ESPERADO
```

Selecione so as colunas necessarias; arrastar `title`/`doi`/`year` dos dois
lados polui a tabela. O `assert` pega as duas falhas silenciosas do merge:
menos linhas significa id que nao casou, mais linhas significa id duplicado
em um dos arquivos multiplicando o n e contaminando o kappa.

**Antes de comparar, inspecione o vocabulario dos dois lados:**

```python
print(d["decision_a"].value_counts(dropna=False))
print(d["decision_b"].value_counts(dropna=False))
```

`dropna=False` e obrigatorio: por padrao o `value_counts` esconde vazios e a
tabela some com registros sem decisao sem avisar.

Arquivos de origens diferentes quase nunca usam os mesmos rotulos
(`Excluded` vs `EXCLUDE` vs `EXC`). Comparacao de texto entre vocabularios
divergentes e sempre valida e sempre falsa: o resultado sai zerado ou
absurdo, sem erro nenhum. Normalize para uma escala comum com `.replace()`
em **colunas novas**, preservando as originais.

**Terceira categoria.** Se um revisor tem "incerto" e o outro nao, o destino
dessas linhas e convencao, nao calculo. Trate incerto como inclusao
provisoria (reflete o fluxo real: incerto segue para texto completo) ou como
exclusao, mas **declare qual convencao foi usada** no texto dos metodos. O
que invalida nao e a escolha, e a omissao. Reportar as duas como analise de
sensibilidade e o mais transparente.

## 2. Concordancia

```python
tab = pd.crosstab(d["a"], d["b"]).reindex(index=["EXC","INC"], columns=["EXC","INC"])
n  = tab.values.sum()
po = np.trace(tab.values) / n
p_lin = tab.sum(axis=1) / n
p_col = tab.sum(axis=0) / n
pe = (p_lin.values * p_col.values).sum()
kappa = (po - pe) / (1 - pe)
```

O `reindex` nao e decoracao: `np.trace` soma a diagonal **por posicao**. Se
uma categoria aparecer so de um lado, as ordens desalinham e o trace soma
celulas erradas sem reclamar.

**Indices complementares**, com a notacao classica em que `a` e `d` sao as
celulas de concordancia (diagonal) e `b` e `c` as de divergencia:

```python
pabak = 2*po - 1
prevalence_index = abs(a - d) / n
bias_index       = abs(b - c) / n
```

Conferencia independente do indice de vies: ele tem que ser igual a
diferenca entre as marginais dos dois revisores dividida por n. Se nao der,
o mapeamento das letras esta trocado — erro comum que inverte os dois
indices.

**Interpretacao.** Em triagem de revisao sistematica a prevalencia e
extrema (tipicamente 90-95% de exclusoes). Isso eleva muito o `pe`, e um
`po` de 93% pode produzir kappa de 0,60. Nao indica revisores mal
calibrados: indica corpus tipico. Reporte kappa **e** PABAK **e** o indice
de prevalencia lado a lado — kappa sozinho convida a conclusao errada;
PABAK sozinho e maquiagem.

Olhe tambem a **assimetria das divergencias**. Divergencia concentrada numa
celula (um revisor sempre mais inclusivo) e diferenca sistematica de limiar,
nao ruido, e merece uma frase no texto.

O que reportar: n de pares, convencao usada para a terceira categoria, `po`,
kappa com faixa interpretativa, PABAK, indice de prevalencia, e numero de
divergencias resolvidas por adjudicacao.

## 3. Adjudicacao e consolidacao

Cruze a lista de divergencias com o arquivo de adjudicacao **nos dois
sentidos**: divergencia sem adjudicacao e registro sem destino definido;
adjudicacao sem divergencia significa que a adjudicacao foi mais ampla que a
resolucao de conflitos da dupla, e o texto precisa dizer isso.

Divergencias orfas costumam ter causa sistematica, nao aleatoria — tipicamente
a regra que montou a lista de adjudicacao usou convencao diferente da do
kappa para a terceira categoria.

**Consolidacao hierarquica**, uma decisao por registro:

```python
final["consenso"]  = np.where(final["a"] == final["b"], final["a"], None)
final["adjudicado"] = final["id"].map(dict(zip(adj["id"], adj["final_norm"])))
final["decisao"]    = final["adjudicado"].fillna(final["consenso"])
final.loc[mask_resolucoes, "decisao"] = ...   # resolucoes posteriores
final["origin"] = np.where(final["adjudicado"].notna(), "adjudicacao", "consenso")
final.loc[mask_resolucoes, "origin"] = "resolucao_posterior"
```

A ordem do `fillna` implementa a prioridade — adjudicacao sobre consenso.
Invertida, o consenso passa por cima da adjudicacao.

A coluna `origin` transforma "confie em mim" em "confira voce mesmo": cada
linha declara de onde veio sua decisao.

**Nunca edite os arquivos brutos a mao.** O arquivo de adjudicacao e registro
historico do que foi decidido naquela sessao, incluindo os casos que ficaram
sem resolucao. Resolucoes posteriores entram como dicionario explicito e
comentado no notebook, e o resultado sai como arquivo novo. Cadeia: brutos
como entrada, notebook como transformacao documentada, consolidado como
fonte unica das etapas seguintes.

## 4. Texto completo

Use criterios de elegibilidade em cascata ("gates"), ordenados do mais barato
ao mais caro de verificar, e **pare no primeiro que reprovar** — registre o
gate decisivo e o motivo, e passe adiante.

Para cada gate registre a **citacao verbatim** que o resolve, no momento em
que encontrar. Achar de novo depois custa dez vezes mais, e e essa citacao
que torna a decisao auditavel.

**Motivo publicavel = criterio + fato especifico do estudo.** "FAIL no E3"
nao e motivo; "estimacao concorrente: preditor e desfecho medidos na mesma
sessao" e. O PRISMA 2020 exige motivo declarado para toda exclusao em texto
completo (e nao exige para a triagem por titulo e resumo — nao gaste tempo
perseguindo rotulos la).

**Criterios subjetivos precisam de regra escrita antes, nao depois.** Se um
gate depender de o artigo *descrever* algo (contexto, protocolo), decida de
antemao se o silencio reprova ou gera duvida, e aplique igual em todos.
Sinal de alerta: quando um criterio elimina preferencialmente os estudos mais
rigorosos, o problema costuma estar no criterio, nao nos estudos.

**Sobreposicao de coorte** e o unico gate que nao se avalia lendo um artigo
isolado — deixe-o por ultimo, depois de todas as fichas preenchidas. Va
anotando quatro marcas por estudo: grupo/primeiro autor, numero de registro
do ensaio, centro de recrutamento, e janela de coleta com o n. Ao fim,
ordene e procure repeticoes. Um artigo que combina subamostras **proprias**
nao e caso de sobreposicao; o caso e dois registros do corpus compartilhando
pacientes. Quando ocorrer: a unidade de analise e o **estudo**, nao o relato
— escolha um relato primario por criterio definido de antemao, trate o outro
como relato companheiro, e nunca some participantes entre eles.

**Analise secundaria de dados de ensaio clinico e elegivel** numa revisao de
modelos preditivos. A fonte dos dados e caracteristica a registrar e avaliar
no PROBAST, nao criterio de exclusao.

Use `scripts/make_screening_tool.py` para gerar a ferramenta HTML de
avaliacao (gates, evidencia verbatim, veredito, exportacao CSV/JSON,
persistencia em localStorage). Decida antes se o avaliador vera pareceres
anteriores: avaliacao independente permite reportar concordancia entre
passadas; conferencia sobre parecer pronto e mais rapida mas deve ser
descrita como conferencia nos metodos.

## 5. PRISMA

**Separe as duas etapas de exclusao.** Registro excluido na triagem por
titulo e resumo e registro excluido apos leitura do texto completo vao em
caixas diferentes. Um registro que foi buscado, teve o PDF baixado e so
depois foi excluido pertence a segunda — sobrescrever a decisao da triagem
faz ele sumir da caixa de "buscados" e a cadeia nao fecha. Use colunas
separadas: `final_decision` para a triagem, `fulltext_decision` e
`fulltext_reason` para a leitura.

**Terminologia do PRISMA 2020**, verificada por editor com frequencia:
*records* sao registros bibliograficos (identificados, desduplicados,
triados); *reports* sao documentos recuperados (buscados, avaliados,
excluidos no texto completo); *studies* so na caixa final de incluidos.

**Grave os numeros num JSON** e faca figura, tabela e texto lerem dali.
Numero digitado em tres lugares diverge na primeira correcao. Cuidado: `.sum()`
do pandas devolve `numpy.int64`, que o modulo `json` nao serializa —
converta com `int()`.

**Amarre a cadeia com asserts** no notebook, nao com conferencia visual:

```python
assert identificados - duplicatas == triados
assert triados - excluidos_triagem == buscados
assert buscados - excluidos_tc == incluidos
```

Assim qualquer reclassificacao futura quebra na hora, em vez de produzir
silenciosamente um numero diferente do que esta escrito no manuscrito.

Use `scripts/prisma_figure.py` para gerar o diagrama a partir do JSON.

## Erros silenciosos: checklist

Todos estes **nao levantam excecao**. Sao os que custam mais caro.

- **Vocabulario divergente entre arquivos.** `Excluded` != `EXCLUDE` != `EXC`.
  Sempre `value_counts()` nos dois lados antes de comparar.
- **Tipo de `id` incompativel.** `int64` de um lado e `object` do outro faz
  `.isin()` retornar tudo `False` e `.map()` retornar tudo vazio. Confira
  `dtype` antes.
- **Sobrescrever coluna com significado diferente.** Guardar consenso e
  adjudicacao no mesmo nome destrui um dos dois. Nome de coluna e significado,
  nao espaco de armazenamento.
- **Trocar chaves ao mapear texto por id.** Identificadores numericos longos
  sao indistinguiveis a olho. Sempre imprima o **titulo** ao lado do texto na
  conferencia.
- **`value_counts()` sem `dropna=False`** esconde registros sem decisao.
- **Filtro sem `.copy()`** antes de atribuir coluna gera
  `SettingWithCopyWarning` e atribuicao que nao surte efeito.
- **Notebook copiado de outro** carrega variaveis com nomes iguais e
  significados diferentes. Um notebook, uma historia; a interface entre eles
  e um arquivo.
