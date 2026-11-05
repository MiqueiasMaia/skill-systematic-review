#!/usr/bin/env python3
"""Gera uma ferramenta HTML de triagem de texto completo.

Uso:
    python make_screening_tool.py --records records.csv --pdf-dir pdf \
        --gates gates.json --out 03-fulltext-screening.html

records.csv  colunas minimas: id,title  (doi,year opcionais)
gates.json   lista de [codigo, nome, descricao], na ordem de avaliacao
             (do criterio mais barato de verificar ao mais caro)

A ferramenta grava em localStorage (chave --key) e exporta CSV e JSON.
Os PDFs sao casados por titulo normalizado; o HTML deve ficar na pasta que
contem --pdf-dir, porque os links sao relativos.
"""
import argparse, csv, json, os, re, unicodedata

DEFAULT_GATES = [
    ["E1", "Populacao", "A amostra corresponde a populacao-alvo da revisao."],
    ["E2", "Desenho", "O desenho do estudo e elegivel."],
    ["E3", "Desfecho", "O desfecho e o especificado no protocolo."],
]

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#1a1d21;background:#f4f6f8}
#wrap{display:flex;height:100vh}
#side{width:310px;flex:none;background:#fff;border-right:1px solid #dfe3e8;display:flex;flex-direction:column}
#side header{padding:14px 16px;border-bottom:1px solid #dfe3e8}
#side h1{font-size:14px;margin:0 0 8px;font-weight:600}
#prog{font-size:12px;color:#5a6672}
#bar{height:4px;background:#e7ebef;border-radius:2px;margin-top:8px;overflow:hidden}
#bar div{height:100%;background:#2563a8;width:0;transition:width .2s}
#list{overflow-y:auto;flex:1}
.item{padding:9px 14px;border-bottom:1px solid #eef1f4;cursor:pointer;display:flex;gap:8px;align-items:flex-start}
.item:hover{background:#f7f9fb}
.item.sel{background:#eaf2fb;box-shadow:inset 3px 0 0 #2563a8}
.item .t{font-size:12px;line-height:1.35;color:#333;flex:1}
.dot{width:9px;height:9px;border-radius:50%;flex:none;margin-top:4px;background:#cfd6dd}
.dot.INCLUDE{background:#1d8a4e}.dot.EXCLUDE{background:#b3271e}.dot.UNCERTAIN{background:#d4860b}
#main{flex:1;overflow-y:auto;padding:22px 30px 90px}
.card{background:#fff;border:1px solid #dfe3e8;border-radius:6px;padding:18px 20px;margin-bottom:16px;max-width:900px}
h2{font-size:17px;margin:0 0 6px;line-height:1.35}
.meta{font-size:12px;color:#5a6672;margin-bottom:12px}
.meta a{color:#2563a8}
.btn{display:inline-block;padding:7px 13px;border:1px solid #c6ced6;background:#fff;border-radius:5px;cursor:pointer;font-size:13px;text-decoration:none;color:#1a1d21}
.btn:hover{background:#f2f5f8}
.btn.pdf{background:#2563a8;color:#fff;border-color:#2563a8;font-weight:500}
.gate{border-top:1px solid #eef1f4;padding:13px 0}
.gate:first-of-type{border-top:none}
.gname{font-weight:600;font-size:13px;margin-bottom:2px}
.gdesc{font-size:12px;color:#5a6672;margin-bottom:8px}
.opts{display:flex;gap:6px;margin-bottom:7px}
.opt{padding:5px 12px;border:1px solid #c6ced6;border-radius:4px;background:#fff;cursor:pointer;font-size:12px}
.opt.on.PASS{background:#1d8a4e;color:#fff;border-color:#1d8a4e}
.opt.on.FAIL{background:#b3271e;color:#fff;border-color:#b3271e}
.opt.on.UNCLEAR{background:#d4860b;color:#fff;border-color:#d4860b}
textarea{width:100%;border:1px solid #d5dbe1;border-radius:4px;padding:7px;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;resize:vertical}
.vrow{display:flex;gap:8px;margin:10px 0}
.v{padding:9px 18px;border:1px solid #c6ced6;border-radius:5px;background:#fff;cursor:pointer;font-weight:600;font-size:13px}
.v.on.INCLUDE{background:#1d8a4e;color:#fff;border-color:#1d8a4e}
.v.on.EXCLUDE{background:#b3271e;color:#fff;border-color:#b3271e}
.v.on.UNCERTAIN{background:#d4860b;color:#fff;border-color:#d4860b}
label{display:block;font-size:12px;font-weight:600;margin:10px 0 4px;color:#3a434d}
select,input[type=text]{width:100%;padding:7px;border:1px solid #d5dbe1;border-radius:4px;font-size:13px;background:#fff}
#hint{font-size:12px;color:#8a5a00;background:#fff8e6;border:1px solid #f0dca8;border-radius:4px;padding:8px 10px;margin:10px 0;display:none}
#foot{position:fixed;bottom:0;left:310px;right:0;background:#fff;border-top:1px solid #dfe3e8;padding:10px 30px;display:flex;gap:10px;align-items:center}
#saved{font-size:12px;color:#1d8a4e;margin-left:auto}
</style></head><body><div id="wrap">
<div id="side"><header><h1>__TITLE__</h1>
<div id="prog"></div><div id="bar"><div></div></div></header><div id="list"></div></div>
<div id="main"></div></div>
<div id="foot">
<button class="btn" onclick="go(-1)">&larr; Anterior</button>
<button class="btn" onclick="go(1)">Proximo &rarr;</button>
<button class="btn" onclick="exportCSV()">Exportar CSV</button>
<button class="btn" onclick="exportJSON()">Exportar JSON</button>
<span id="saved"></span></div>
<script>
const DATA = __DATA__;
const GATES = __GATES__;
const KEY = "__KEY__";
let state = JSON.parse(localStorage.getItem(KEY) || "{}");
let cur = 0;
function save(){ localStorage.setItem(KEY, JSON.stringify(state));
  const s=document.getElementById("saved"); s.textContent="salvo "+new Date().toLocaleTimeString();
  setTimeout(()=>s.textContent="",2500); renderList(); }
function rec(i){ const id=DATA[i].id; if(!state[id]) state[id]={gates:{},evid:{},verdict:"",deciding:"",reason:"",notes:""}; return state[id]; }
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function renderList(){
  const L=document.getElementById("list"); L.innerHTML=""; let done=0;
  DATA.forEach((d,i)=>{ const r=state[d.id]; const v=r&&r.verdict?r.verdict:""; if(v) done++;
    const el=document.createElement("div"); el.className="item"+(i===cur?" sel":"");
    el.innerHTML='<span class="dot '+v+'"></span><span class="t">'+(d.year||"")+' &mdash; '+esc(String(d.title).slice(0,78))+'</span>';
    el.onclick=()=>{cur=i;render();}; L.appendChild(el); });
  document.getElementById("prog").textContent=done+" de "+DATA.length+" avaliados";
  document.querySelector("#bar div").style.width=(100*done/DATA.length)+"%";
}
function render(){
  const d=DATA[cur], r=rec(cur);
  let h='<div class="card"><h2>'+esc(d.title)+'</h2><div class="meta">Registro '+(cur+1)+' de '+DATA.length+
    ' &nbsp;&middot;&nbsp; id '+d.id+' &nbsp;&middot;&nbsp; '+(d.year||"s/ano")+
    (d.doi?' &nbsp;&middot;&nbsp; <a href="https://doi.org/'+esc(d.doi)+'" target="_blank">'+esc(d.doi)+'</a>':'')+'</div>'+
    (d.pdf?'<a class="btn pdf" href="__PDFDIR__/'+encodeURIComponent(d.pdf)+'" target="_blank">Abrir PDF</a>':'<em>PDF nao localizado</em>')+
    '</div><div class="card">';
  GATES.forEach((g,gi)=>{ const sel=r.gates[g[0]]||"";
    h+='<div class="gate"><div class="gname">Gate '+(gi+1)+' &mdash; '+g[1]+' ('+g[0]+')</div>'+
       '<div class="gdesc">'+esc(g[2])+'</div><div class="opts">'+
       ["PASS","FAIL","UNCLEAR"].map(o=>'<button class="opt '+o+(sel===o?" on":"")+'" onclick="setGate(\''+g[0]+'\',\''+o+'\')">'+o+'</button>').join("")+
       '</div><textarea rows="2" placeholder="evidencia / citacao verbatim" oninput="setEvid(\''+g[0]+'\',this.value)">'+esc(r.evid[g[0]]||"")+'</textarea></div>'; });
  h+='</div><div class="card"><div id="hint"></div><label>Veredito</label><div class="vrow">'+
     ["INCLUDE","EXCLUDE","UNCERTAIN"].map(v=>'<button class="v '+v+(r.verdict===v?" on":"")+'" onclick="setV(\''+v+'\')">'+v+'</button>').join("")+
     '</div><label>Gate decisivo (se exclusao)</label><select onchange="setF(\'deciding\',this.value)"><option value="">&mdash;</option>'+
     GATES.map(g=>'<option value="'+g[0]+'"'+(r.deciding===g[0]?" selected":"")+'>'+g[0]+' &mdash; '+g[1]+'</option>').join("")+
     '</select><label>Motivo (criterio + fato especifico do estudo)</label>'+
     '<input type="text" value="'+esc(r.reason||"")+'" oninput="setF(\'reason\',this.value)">'+
     '<label>Observacoes</label><textarea rows="4" oninput="setF(\'notes\',this.value)">'+esc(r.notes||"")+'</textarea></div>';
  document.getElementById("main").innerHTML=h; document.getElementById("main").scrollTop=0;
  hint(); renderList();
}
function hint(){
  const r=rec(cur); const el=document.getElementById("hint"); if(!el) return;
  const f=GATES.filter(g=>r.gates[g[0]]==="FAIL").map(g=>g[0]);
  const u=GATES.filter(g=>r.gates[g[0]]==="UNCLEAR").map(g=>g[0]);
  const n=GATES.filter(g=>!r.gates[g[0]]).length;
  let m=[]; if(f.length) m.push("Gates reprovados: "+f.join(", ")+".");
  if(u.length) m.push("Gates em duvida: "+u.join(", ")+".");
  if(n) m.push(n+" gate(s) sem marcacao.");
  el.style.display=m.length?"block":"none"; el.textContent=m.join(" ");
}
function setGate(g,v){ const r=rec(cur); r.gates[g]=(r.gates[g]===v?"":v); save(); render(); }
function setEvid(g,v){ rec(cur).evid[g]=v; save(); }
function setV(v){ const r=rec(cur); r.verdict=(r.verdict===v?"":v); r.ts=new Date().toISOString(); save(); render(); }
function setF(k,v){ rec(cur)[k]=v; save(); }
function go(n){ cur=Math.max(0,Math.min(DATA.length-1,cur+n)); render(); }
document.addEventListener("keydown",e=>{ const t=e.target.tagName;
  if(t==="TEXTAREA"||t==="INPUT"||t==="SELECT") return;
  if(e.key==="ArrowLeft")go(-1); if(e.key==="ArrowRight")go(1); });
function rows(){
  const head=["id","year","doi","title","verdict","deciding_gate","reason"]
    .concat(GATES.map(g=>"gate_"+g[0])).concat(GATES.map(g=>"evid_"+g[0])).concat(["notes","timestamp"]);
  const out=[head];
  DATA.forEach(d=>{ const r=state[d.id]||{gates:{},evid:{}};
    out.push([d.id,d.year,d.doi,d.title,r.verdict||"",r.deciding||"",r.reason||""]
      .concat(GATES.map(g=>(r.gates||{})[g[0]]||""))
      .concat(GATES.map(g=>(r.evid||{})[g[0]]||""))
      .concat([r.notes||"",r.ts||""])); });
  return out;
}
function dl(name,text,type){ const b=new Blob([text],{type:type});
  const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download=name; a.click(); }
function exportCSV(){
  const csv=rows().map(r=>r.map(c=>'"'+String(c==null?"":c).replace(/"/g,'""')+'"').join(",")).join("\n");
  dl("fulltext_screening.csv","\ufeff"+csv,"text/csv;charset=utf-8"); }
function exportJSON(){ dl("fulltext_screening.json",JSON.stringify(state,null,2),"application/json"); }
renderList(); render();
</script></body></html>"""


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def match_pdfs(records, pdf_dir):
    if not pdf_dir or not os.path.isdir(pdf_dir):
        return records, []
    pdfs = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
    index = {norm(f[:-4]): f for f in pdfs}
    missing = []
    for r in records:
        k = norm(r["title"])
        hit = index.get(k)
        if not hit:
            cands = [v for kk, v in index.items() if kk and (kk.startswith(k[:60]) or k.startswith(kk[:60]))]
            hit = cands[0] if len(cands) == 1 else None
        r["pdf"] = hit or ""
        if not hit:
            missing.append(r["id"])
    return records, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--pdf-dir", default="pdf")
    ap.add_argument("--gates", default=None)
    ap.add_argument("--out", default="fulltext_screening.html")
    ap.add_argument("--key", default="fulltext_screen_v1")
    ap.add_argument("--title", default="Triagem de texto completo")
    a = ap.parse_args()

    with open(a.records, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    records = [{"id": str(r["id"]), "title": r["title"],
                "doi": r.get("doi", ""), "year": r.get("year", "")} for r in rows]
    records.sort(key=lambda r: (str(r["year"]), r["title"]))
    records, missing = match_pdfs(records, a.pdf_dir)

    gates = json.load(open(a.gates, encoding="utf-8")) if a.gates else DEFAULT_GATES

    html = (TEMPLATE
            .replace("__DATA__", json.dumps(records, ensure_ascii=False))
            .replace("__GATES__", json.dumps(gates, ensure_ascii=False))
            .replace("__KEY__", a.key)
            .replace("__PDFDIR__", a.pdf_dir)
            .replace("__TITLE__", a.title))
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("escrito:", a.out, "|", len(records), "registros |", len(gates), "gates")
    if missing:
        print("sem PDF:", missing)


if __name__ == "__main__":
    main()
