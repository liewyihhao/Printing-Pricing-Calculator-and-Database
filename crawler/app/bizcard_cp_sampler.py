"""Business Card (1) EXACT sampler via direct /Product/CheckPrice.
Schema captured live: type='Business Card'. The order-form v4 page has no window.metrics,
so option values are read from the page selects and transformed to the API's value format
(Size ×→x, Paper strips ' (...)' suffix, Package 'N In 1 (N Designs)'→'Nin1', qty strips
' — Best Seller'/commas). Enumerate the cartesian product; invalid combos return None."""
import json, re, sys, asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from app import checkprice_enum as C
from app import voucher_cp_sampler as V

OUT = Path(__file__).resolve().parent.parent / "output"
SIZES=["54mm × 89mm","52mm × 86mm","50mm × 89mm","54mm × 86mm"]
PAPERS=["Gloss Art Card 250gsm (2 side coated)","Gloss Art Card 310gsm (2 side coated)","Gloss Art Card 360gsm (2 side coated)","Matte Art Card 250gsm","Linen 240gsm","Metal Ice 250gsm","Synthetic Paper 180micron (0.18mm)","Super White 250gsm","Suwen 240gsm"]
COLOURS=["4C (Both)","4C (Front)"]
LAMS=["Gloss Lamination (Both)","Matte Lamination (Both)","Gloss Water Based Varnish (Both)(Free)"]
PKGS=["Normal (1 Design)","2 In 1 (2 Designs)","3 In 1 (3 Designs)","4 In 1 (4 Designs)","5 In 1 (5 Designs)","6 In 1 (6 Designs)","7 In 1 (7 Designs)","8 In 1 (8 Designs)","9 In 1 (9 Designs)","10 In 1 (10 Designs)"]
QTYS=["50","100","200","300","400","500","600","700","800","900","1000","2000","3000","4000","5000","6000","7000","8000","9000","10000"]

def _size(v): return v.replace("×","x").strip()
def _paper(v): return re.sub(r"\s*\([^)]*\)\s*$","",v).strip()
def _lam(v): return re.sub(r"\(Free\)","",v).strip()
def _pkg(v):
    if v.lower().startswith("normal"): return "Normal"
    m=re.match(r"(\d+)\s*In\s*1", v, re.I); return f"{m.group(1)}in1" if m else v

def spec_for(size,paper,colour,lam,pkg,qty):
    return {"Product":"Business Card","OrderDesc":"Standard","Size":_size(size),"Orientation":"Landscape",
            "Paper":_paper(paper),"Package":_pkg(pkg),"PrintColour":colour,"Quantity":qty,"Lamination":_lam(lam),
            "HotStamping":"","HotStampingColour":"","HotStampingBlock":"","RoundCorner":"","HolePunch":"",
            "Embossing":"","Folding":"","FoldCode":"","Country":"99","Courier":"DEFAULT","CountryZone":"West Malaysia"}

CKPT = OUT / "bizcard_cp_samples.json"


def run(max_workers=2):  # CheckPrice not concurrency-safe: workers<=2 (see memory)
    cookie=V._get_session_cookie()
    curves={}
    if CKPT.exists():
        try:
            curves=json.loads(CKPT.read_text(encoding="utf-8"))
            print(f"resumed {sum(len(v) for v in curves.values())} pts", file=sys.stderr)
        except Exception: pass
    tasks=[]
    for size in SIZES:
      for paper in PAPERS:
        for colour in COLOURS:
          for lam in LAMS:
            for pkg in PKGS:
              key=f"{_size(size)}|{_paper(paper)}|{colour}|{_lam(lam)}|{_pkg(pkg)}"
              for q in QTYS:
                if q not in curves.get(key,{}):
                    tasks.append((key,q,spec_for(size,paper,colour,lam,pkg,q)))
    print(f"business-card: {len(tasks)} CheckPrice calls pending", file=sys.stderr)
    done=fail=0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs={ex.submit(C._fetch,"Business Card",s,cookie):(k,q) for k,q,s in tasks}
        for fu in as_completed(futs):
            k,q=futs[fu]; p=fu.result()
            if p: curves.setdefault(k,{})[q]=p
            else: fail+=1
            done+=1
            if done%2000==0:
                CKPT.write_text(json.dumps(curves))
                print(f"  {done}/{len(tasks)} ({fail} none)", file=sys.stderr)
    CKPT.write_text(json.dumps(curves))
    curves={k:v for k,v in curves.items() if v}
    axes=["Size","Paper","Print Colour","Lamination","Package"]
    dist={a:list(dict.fromkeys(k.split("|")[i] for k in curves)) for i,a in enumerate(axes)}
    deps={}
    for k in curves:
        p=k.split("|"); sub=deps.setdefault(p[0],{a:[] for a in axes[1:]})
        for a,v in zip(axes[1:],p[1:]):
            if v not in sub[a]: sub[a].append(v)
    out={"slug":"business-card","source":"checkprice-api","rows":sum(len(c) for c in curves.values()),
         "optionCols":axes,"primary":"Size","deps":deps,"imageField":None,"distinct":dist,"imageOptions":{},
         "priceMeta":{"priceCol":"Price","qtyCol":"Quantity","axisCols":axes,"nCurves":len(curves)},"curves":curves}
    (OUT/"v4_options"/"business-card_options.json").write_text(json.dumps(out))
    print(f"wrote business-card_options.json: {len(curves)} curves ({fail} none of {done})", file=sys.stderr)

if __name__=="__main__": run()
