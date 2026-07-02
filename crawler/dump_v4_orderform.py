"""Dump visible select/radio options for a v4 'Order Form' legacy-template page
(same family as Cap/ID Card) — used only for options-complete contact-for-quote
listings since exact pricing automation is a separate follow-up task."""
import asyncio
import json
import sys
from playwright.async_api import async_playwright
from app import browser as B


async def main(url):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()
        ok = await B.login(page)
        print("login ok:", ok, file=sys.stderr)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1200)
        info = await page.evaluate("""() => {
            const selects = [...document.querySelectorAll('select')].filter(s=>s.offsetParent && s.options.length>1).map(s=>({
                id: s.id, options: [...s.options].map(o=>o.text.trim()).filter(t=>t && !/please select/i.test(t))
            })).filter(s=>!/country/i.test(s.id));
            const radios = {};
            document.querySelectorAll('input[type=radio]').forEach(r=>{
                if(!r.offsetParent) return;
                const label = r.closest('label')?.textContent?.trim() || r.parentElement?.textContent?.trim() || r.value;
                (radios[r.name] ||= []).push(label);
            });
            const filteredRadios = Object.fromEntries(Object.entries(radios).filter(([k,v])=>v.length>1 && !/country|courier/i.test(k)));
            return {title: document.title, selects, radios: filteredRadios};
        }""")
        print(json.dumps(info, indent=2))
        await b.close()

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
