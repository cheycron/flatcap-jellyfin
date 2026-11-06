// Screenshots of the demo server with a Flatcap CSS set through Dashboard -> Branding -> Custom CSS (API, throwaway server only).
//   node qa/shoot.mjs <css file | none> <base theme dark|light> <emulated scheme dark|light> <out dir> [view,view,...]
import fs from 'fs';
import { launch, login, BASE, setBrandingCss, items } from './lib.mjs';
import { views } from './views.mjs';

const [, , cssFile, baseTheme = 'dark', scheme = 'dark', outDir = '/tmp/fc-jf/shots', only] = process.argv;
fs.mkdirSync(outDir, { recursive: true });
await setBrandingCss(cssFile && cssFile !== 'none' ? fs.readFileSync(cssFile, 'utf8') : '');
const ctx = await items();
const { b, p } = await launch({ scheme });
await login(p);
await p.evaluate(([u, t]) => { localStorage.setItem(`${u}-appTheme`, t); localStorage.setItem(`${u}-dashboardTheme`, t); }, [ctx.uid, baseTheme]);
const V = views(p, ctx);
for (const k of (only ? only.split(',') : Object.keys(V))) {
  try { await V[k](); await p.screenshot({ path: `${outDir}/${k}.png` }); console.log('ok', k); } catch (e) { console.log('FAIL', k, String(e).split('\n')[0]); }
}
await b.close();
