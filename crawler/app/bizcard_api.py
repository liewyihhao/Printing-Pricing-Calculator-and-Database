"""Direct client for the v4 Excard pricing API (Product/CheckPrice).

Discovered from v4.excard.com.my/scripts/v4/get-price.js — the SPA POSTs a JSON
spec to a pricing service with a FIXED api credential (no member login needed),
and gets back the cash/before-discount Price. We call it directly: no browser,
fast, exact. This is the Excard REFERENCE price (we still build our own formula).

  price(spec_dict) -> float | None     # RM cash (before discount), None if invalid
"""
from __future__ import annotations
import base64, json, ssl, time
import urllib.request, urllib.error

CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_HDR = {
    "Authorization": "Basic " + base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode(),
    "Api-Key": "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ",
    "Content-Type": "application/json; charset=utf-8",
}
_CTX = ssl._create_unverified_context()

# Full spec template (all keys the API expects); callers override what they vary.
SPEC_TEMPLATE = {
    "Product": "Business Card", "OrderDesc": "Standard", "Size": "", "Orientation": "Landscape",
    "Paper": "", "Quantity": "300", "Package": "Normal", "PrintColour": "4C (Both)",
    "Lamination": "", "HotStamping": "", "HotStampingColour": "", "HotStampingFrontColour1": "",
    "HotStampingFrontColour2": "", "HotStampingBackColour1": "", "HotStampingBackColour2": "",
    "HotStampingBlock": "", "RoundCorner": "", "HolePunch": "", "Embossing": "",
    "Folding": "", "FoldCode": "", "Country": "99", "Courier": "Default", "IsCustomSize": "false",
}


def check_price(spec: dict, kind: str = "Business card", retries: int = 3) -> dict | None:
    """POST one spec; return the full response dict (Price, Weight, ...) or None."""
    body = json.dumps({"type": kind, "spec": [spec]}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(CHECKPRICE_URL, data=body, headers=_HDR, method="POST")
            with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
                d = json.loads(r.read().decode())
                return d.get("d", d) if isinstance(d, dict) else d
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == retries - 1:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def price(spec: dict) -> float | None:
    """Cash (before-discount) RM for a spec, or None if invalid/zero."""
    d = check_price(spec)
    if not d:
        return None
    try:
        p = float(str(d.get("Price", "0")).replace(",", ""))
        return p if p > 0 else None
    except (TypeError, ValueError):
        return None


def make_spec(**overrides) -> dict:
    s = dict(SPEC_TEMPLATE)
    s.update(overrides)
    return s


if __name__ == "__main__":
    s = make_spec(Size="54mm x 89mm", Paper="Gloss Art Card 250gsm",
                  Lamination="Gloss Waterbase Varnish (Both)", Quantity="300")
    print("sample price:", price(s))
