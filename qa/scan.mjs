// Computed-color scan of every visible element in each view. Writes JSON: view -> "prop|value" -> {n, ex[]}.
//   node qa/scan.mjs <css file | none> <base theme> <emulated scheme> <out.json>
import fs from 'fs';
import { launch, login, setBrandingCss, items } from './lib.mjs';
import { views } from './views.mjs';

const [, , cssFile, baseTheme = 'dark', scheme = 'dark', out = '/tmp/fc-jf/scan.json'] = process.argv;
await setBrandingCss(cssFile && cssFile !== 'none' ? fs.readFileSync(cssFile, 'utf8') : '');
const ctx = await items();
const { b, p } = await launch({ scheme });
await login(p);
await p.evaluate(([u, t]) => { localStorage.setItem(`${u}-appTheme`, t); localStorage.setItem(`${u}-dashboardTheme`, t); }, [ctx.uid, baseTheme]);
const V = views(p, ctx);
const res = {};
const scan = () => p.evaluate(() => {
  const o = {};
  const add = (prop, v, e) => {
    if (!v || v === 'rgba(0, 0, 0, 0)' || v === 'none' || v.startsWith('linear-gradient') && false) return;
    const k = `${prop}|${v}`; const r = (o[k] ||= { n: 0, ex: [] }); r.n++;
    const id = e.tagName.toLowerCase() + (e.className && e.className.baseVal === undefined ? '.' + String(e.className).trim().split(/\s+/).slice(0, 2).join('.') : '');
    if (r.ex.length < 3 && !r.ex.includes(id)) r.ex.push(id);
  };
  for (const e of document.body.querySelectorAll('*')) {
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    if (r.width < 1 || r.height < 1 || cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
    const hasText = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (hasText || e.matches('svg,svg *,button,input,select,.material-icons')) add('color', cs.color, e);
    add('background-color', cs.backgroundColor, e);
    if (/gradient/.test(cs.backgroundImage)) add('background-image', cs.backgroundImage.replace(/\s+/g, ' ').slice(0, 120), e);
    for (const side of ['Top', 'Bottom', 'Left', 'Right']) if (parseFloat(cs[`border${side}Width`]) > 0 && cs[`border${side}Style`] !== 'none') { add('border-color', cs[`border${side}Color`], e); break; }
    if (cs.fill && cs.fill !== 'none' && e.closest('svg')) add('fill', cs.fill, e);
  }
  return o;
});
for (const k of Object.keys(V)) {
  try { await V[k](); res[k] = await scan(); console.log('ok', k, Object.keys(res[k]).length); } catch (e) { console.log('FAIL', k, String(e).split('\n')[0]); }
}
fs.writeFileSync(out, JSON.stringify(res));
await b.close();
