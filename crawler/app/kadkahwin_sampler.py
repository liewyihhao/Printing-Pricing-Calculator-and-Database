"""Kad Kahwin (114) EXACT sampler via direct /Product/CheckPrice.
Schema captured from the live page: type='Kad Kahwin', Size strips the 'XX (' prefix,
Paper strips the ' (...)' suffix, OrderDesc='Standard'. Price axes = Size×Paper×PrintColour
(Lamination/Folding/Finishing/Envelope/HotStamping are price-neutral / quoted separately)."""
import json, re, sys, asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from app import checkprice_enum as C
from app.readymade_enum import login_v4
from playwright.async_api import async_playwright
from app import browser as B

OUT = Path(__file__).resolve().parent.parent / "output"
QTYS = ["10","20","30","40","50","60","70","80","90","100","150","200","250","300","400","500","700","1000"]
# Lamination is a real price axis (Front ~+8%, Both ~+16%; 0 on non-laminatable papers like
# Linen; Gloss==Matte at equal coverage). Sample all 5 so no mapping assumption is made.
LAMS=[("Not Required",""),("Gloss Lamination (Front)","Gloss Lamination (Front)"),
      ("Gloss Lamination (Both)","Gloss Lamination (Both)"),
      ("Matte Lamination (Front)","Matte Lamination (Front)"),
      ("Matte Lamination (Both)","Matte Lamination (Both)")]

def _size(v): 
    m = re.search(r"\(([^)]+)\)", v); return m.group(1) if m else v
def _paper(v): return re.sub(r"\s*\([^)]*\)\s*$", "", v)

async def _axes_and_cookie():
    async with async_playwright() as pw:
        b=await B.launch(pw); page=await b.new_page(); await login_v4(page)
        await page.goto("https://v4.excard.com.my/ordering/kad-kahwin", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_function("()=>Array.isArray(window.metrics)&&window.metrics.length>0", timeout=60000)
        # distinct valid Size|Paper|PrintColour combos, computed in-browser
        combos=await page.evaluate("""()=>{const m=window.metrics,s=new Set();for(const r of m)s.add([r['Size'],r['Paper'],r['Print Colour']].join('\u0001'));return [...s];}""")
        cookies=await page.context.cookies()
        cookie="; ".join(f"{c['name']}={c['value']}" for c in cookies if "excard" in c.get("domain","").lower())
        await b.close()
        return combos, cookie

def run(max_workers=2):  # CheckPrice not concurrency-safe: workers<=2
    combos, cookie = asyncio.run(_axes_and_cookie())
    print(f"kad-kahwin: {len(combos)} Size×Paper×Colour combos", file=sys.stderr)
    tasks=[]
    for ck in combos:
        size,paper,colour = ck.split("")
        for lam_label,lam_api in LAMS:
            for q in QTYS:
                spec={"Product":"Kad Kahwin","Size":_size(size),"Paper":_paper(paper),"OrderDesc":"Standard",
                      "PrintColour":colour,"Quantity":q,"Lamination":lam_api,"FoldCode":"","HotStamping":"",
                      "HotStampingSize1":"N/A","HotStampingSize2":"N/A","Envelope":"",
                      "Country":"99","Courier":"DEFAULT","CountryZone":"West Malaysia"}
                tasks.append((f"{size}|{paper}|{colour}|{lam_label}", q, spec))
    curves={}; done=fail=0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs={ex.submit(C._fetch,"Kad Kahwin",s,cookie):(k,q) for k,q,s in tasks}
        for fu in as_completed(futs):
            k,q=futs[fu]; p=fu.result()
            if p: curves.setdefault(k,{})[q]=p
            else: fail+=1
            done+=1
            if done%500==0: print(f"  {done}/{len(tasks)} ({fail} failed)", file=sys.stderr)
    axes=["Size","Paper","Print Colour","Lamination"]
    dist={a:list(dict.fromkeys(k.split("|")[i] for k in curves)) for i,a in enumerate(axes)}
    deps={}
    for k in curves:
        pv=k.split("|")[0]; sub=deps.setdefault(pv,{"Paper":[],"Print Colour":[],"Lamination":[]})
        for a,v in zip(axes[1:],k.split("|")[1:]):
            if v not in sub[a]: sub[a].append(v)
    out={"slug":"kad-kahwin","source":"checkprice-api","rows":sum(len(c) for c in curves.values()),
         "optionCols":axes,"primary":"Size","deps":deps,"imageField":None,"distinct":dist,"imageOptions":{},
         "priceMeta":{"priceCol":"Price","qtyCol":"Quantity","axisCols":axes,"nCurves":len(curves)},"curves":curves}
    (OUT/"v4_options"/"kad-kahwin_options.json").write_text(json.dumps(out))
    print(f"wrote kad-kahwin_options.json: {len(curves)} curves ({fail} failed)", file=sys.stderr)

if __name__=="__main__": run()
