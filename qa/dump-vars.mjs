// Dump the runtime --jf-* custom properties of :root for the built-in themes (dark, light, ...).
//   node qa/dump-vars.mjs out.json
// The web client sets them from its MUI theme (not from themes/<name>/theme.css), so they only exist at runtime.
import { launch, login, BASE, items, admin, api, save } from './lib.mjs';

const out = {};
const { b, p } = await launch({ scheme: 'dark' });
await login(p);
const { token, uid } = await admin();
const themes = ['dark', 'light', 'blueradiance', 'purplehaze', 'appletv', 'wmc'];
for (const t of themes) {
  await p.evaluate(([u, t]) => { localStorage.setItem(`${u}-appTheme`, t); localStorage.setItem(`${u}-dashboardTheme`, t); }, [uid, t]);
  await p.goto(`${BASE}/web/#/home.html`);
  await p.reload();
  await p.waitForTimeout(5000);
  await p.screenshot({ path: `/tmp/fc-jf/theme-${t}.png` });
  out[t] = await p.evaluate(() => {
    const vars = {};
    // custom properties declared on :root by any stylesheet or inline style
    const names = new Set();
    for (const ss of document.styleSheets) {
      let rules; try { rules = ss.cssRules; } catch { continue; }
      const walk = (rs) => { for (const r of rs) { if (r.cssRules && !r.style) walk(r.cssRules); if (r.style) for (const n of r.style) if (n.startsWith('--jf')) names.add(n); } };
      walk(rules);
    }
    const cs = getComputedStyle(document.documentElement);
    for (const n of names) vars[n] = cs.getPropertyValue(n).trim();
    return { vars, link: [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.href).filter((h) => h.includes('theme')), styles: [...document.querySelectorAll('style')].map((s) => s.id || s.className || s.textContent.slice(0, 60)).slice(0, 20) };
  });
}
save(process.argv[2] || '/tmp/fc-jf/runtime-vars.json', out);
await b.close();
