// Node pricing worker: reads {product_id, options, quantity} JSON on stdin, computes the
// quote with the calculator's exact engine + reference markup, writes JSON on stdout.
const path = require('path');
const { DATA, localQuote, tiers } = require(path.join(__dirname, '..', 'output', 'calculator_engine.cjs'));

let buf = '';
process.stdin.on('data', d => buf += d).on('end', () => {
  let req; try { req = JSON.parse(buf || '{}'); } catch (e) { return out({ error: 'invalid JSON body' }); }
  const prod = DATA.products.find(p => p.id === req.product_id);
  if (!prod) return out({ error: 'unknown product_id' }, 404);
  const qty = parseInt(req.quantity, 10);
  if (!qty || qty < 1) return out({ error: 'quantity must be a positive integer' }, 400);
  try {
    const q = localQuote(prod, req.options || {}, qty);
    const mk = prod.markup || 1;
    let cash = q.printoka_cash;
    if (mk !== 1) cash = Math.round(cash * mk * 100) / 100;
    out({
      product_id: prod.id, product: prod.name, quantity: qty, currency: 'MYR',
      pricing_type: mk === 1 ? 'exact' : 'reference',
      cash, per_unit: Math.round((cash / qty) * 1e4) / 1e4,
      tiers: tiers(cash), weight_kg: q.weight_kg
    });
  } catch (e) {
    out({ error: e.message || 'could not price this combination', quote_only: !!e.quote_only }, 422);
  }
});
function out(obj, status) { if (status) obj._status = status; process.stdout.write(JSON.stringify(obj)); }
