"""Direct client for Excard's packaging pricing + dieline APIs (packmage engine).

No browser needed: GET a DIY page to obtain the antiforgery token + cookies, then POST:
  * /uc/GetPriceFactor2  -> exact total/unit price + weight for a box config
  * /uc/LinTest3D        -> the box dieline (LineExp segments + panel dims) for 3D

  price(box, L, W, D, qty, ...) -> {"total","unit","unit_weight","raw"}
  dieline(box, L, W, D)         -> {"BoxJson","LineExp"}
"""
from __future__ import annotations
import json, re, threading
import requests

BASE = "https://packaging.excard.com.my"
DIY = BASE + "/uc/diy/{}"
PRICE = BASE + "/uc/GetPriceFactor2"
LIN = BASE + "/uc/LinTest3D"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149 Safari/537.36"
_TOK_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')

# default process chain (printing 4C on board M0024 + standard processes), per recon
DEFAULT_PROCESS = [
    {"ID": "P001", "Pms": [4, 0, 0, 0, 0], "Materials": [{"MID": "M0024", "SerialNo": 1, "Pms": []}]},
    {"ID": "P021"}, {"ID": "P051"}, {"ID": "P066"},
]
_local = threading.local()


class Packaging:
    """One token+cookie session (reusable; refresh if a call 403s)."""

    def __init__(self, box="A001X", token=None, cookies=None):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "X-Requested-With": "XMLHttpRequest",
                               "Origin": BASE, "Referer": DIY.format(box),
                               "Content-Type": "application/x-www-form-urlencoded"})
        if cookies:
            for k, v in cookies.items():
                self.s.cookies.set(k, v, domain="packaging.excard.com.my")
        # the antiforgery token is issued only inside the logged-in JS flow; callers pass
        # it in via bootstrap_session() (Playwright). Fall back to the page hidden input.
        self.token = token or self._fetch_token(box)

    def _fetch_token(self, box):
        r = self.s.get(DIY.format(box), timeout=30)
        r.raise_for_status()
        m = _TOK_RE.search(r.text)
        return m.group(1) if m else ""

    def price(self, box, L, W, D, qty, cal=0.3, choose=3, color=4,
              material="M0024", process=None, timeout=40):
        proc = json.loads(json.dumps(process or DEFAULT_PROCESS))
        proc[0]["Pms"][0] = color
        proc[0]["Materials"][0]["MID"] = material
        box_diy = [{"BoxID": box, "IsJP": 0, "diyIdx": 1,
                    "BoxPms": f"CHOOSE={choose},L={L},W={W},D={D},CAL={cal}",
                    "Qtys": qty if isinstance(qty, list) else [qty],
                    "ProcessJson": json.dumps(proc)}]
        data = {"boxDiys": json.dumps(box_diy),
                "__RequestVerificationToken": self.token, "__IP": "", "__IP_Isp": ""}
        r = self.s.post(PRICE, data=data, timeout=timeout)
        r.raise_for_status()
        j = r.json()
        if not j.get("success"):
            raise RuntimeError(f"price fail: {j}")
        out = []
        for d in j["Data"]:
            for fee in d.get("LstResFee", []):
                out.append({"box": box, "L": L, "W": W, "D": D, "cal": cal, "color": color,
                            "qty": fee["Qty"], "total": fee["TotalFee"], "unit": fee["UnitFee"],
                            "unit_weight": d.get("UnitWeight"), "profit": d.get("ProfitRate"),
                            "dic": fee.get("DicParams", {})})
        return out

    def dieline(self, box, L, W, D, cal=0.3, choose=3, timeout=40):
        data = {"boxid": box, "boxPms": f"CHOOSE={choose},L={L},W={W},D={D},CAL={cal}",
                "getBoxJson": "true", "getLineExp": "true",
                "__RequestVerificationToken": self.token, "__IP": "", "__IP_Isp": ""}
        r = self.s.post(LIN, data=data, timeout=timeout); r.raise_for_status()
        j = r.json()
        return {"BoxJson": json.loads(j["BoxJson"]) if j.get("BoxJson") else None,
                "LineExp": json.loads(j["LineExp"]) if j.get("LineExp") else None}


async def _bootstrap_async(account_id=1, box="A001X"):
    """Use Playwright (logged into www) to obtain a valid antiforgery token + cookies for
    the packaging subdomain, so plain `requests` can then call the APIs threaded."""
    from playwright.async_api import async_playwright
    from .browser import launch, login
    from . import accounts
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context()
        page = await ctx.new_page()
        try: await login(page, username=a.username, password=a.password)
        except Exception: pass
        await page.goto(DIY.format(box), wait_until="domcontentloaded")
        try: await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception: pass
        import asyncio as _a; await _a.sleep(6)
        token = await page.evaluate(
            "() => { try { return Cm.Cache.get('__RequestVerificationToken'); } catch(e){ return null; } }")
        cookies = {c["name"]: c["value"] for c in await ctx.cookies()
                   if "packaging" in c.get("domain", "")}
        try: await b.close()
        except Exception: pass
        return token, cookies


def bootstrap_session(account_id=1, box="A001X"):
    import asyncio
    token, cookies = asyncio.run(_bootstrap_async(account_id, box))
    return Packaging(box=box, token=token, cookies=cookies)


if __name__ == "__main__":
    pk = bootstrap_session(1)
    print("token len:", len(pk.token), "cookies:", list(pk.s.cookies.keys()))
    for q in (100, 300, 1000):
        rows = pk.price("A001X", 120, 100, 200, q)
        for r in rows:
            print(f"  A001X 120x100x200 q{r['qty']}: total RM{r['total']:.2f} unit RM{r['unit']:.3f} "
                  f"wt {r['unit_weight']:.4f}kg netarea {r['dic'].get('netarea')}")
    dl = pk.dieline("A001X", 120, 100, 200)
    print("dieline panels:", dl["BoxJson"] and {k: dl["BoxJson"][k] for k in ("Width", "Height", "NetArea")},
          "segments:", len(dl["LineExp"]) if dl["LineExp"] else 0)
