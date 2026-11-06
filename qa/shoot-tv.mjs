// Flatcap TV screenshots at 1920x1080 on the THROWAWAY demo server: desktop layout and TV layout (`layout-tv`).
//   node qa/shoot-tv.mjs <css file | none> <out dir> [desktop,tv] [view,view,...] [--je]
// Views: home, library, detail, focus. The layout is chosen the way Jellyfin stores it (localStorage `layout`).
// --je injects a minimal stand-in for the Jellyfin Enhanced header row (only when the plugin is not installed).
import fs from 'fs';
import { launch, login, BASE, setBrandingCss, items } from './lib.mjs';

const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const flags = process.argv.slice(2).filter((a) => a.startsWith('--'));
const [cssFile, outDir = '/tmp/fc-tv/shots', layouts = 'desktop,tv', only] = args;
fs.mkdirSync(outDir, { recursive: true });
await setBrandingCss(cssFile && cssFile !== 'none' ? fs.readFileSync(cssFile, 'utf8') : '');
const ctx = await items();
const { b, p } = await launch({ width: 1920, height: 1080, scheme: 'dark' });
await login(p);
await p.evaluate(([u, bd]) => { localStorage.setItem(`${u}-appTheme`, 'dark'); if (bd === 'false') localStorage.removeItem(`${u}-enableBackdrops`); else localStorage.setItem(`${u}-enableBackdrops`, bd); }, [ctx.uid, process.env.BACKDROPS || 'true']);

const go = async (hash, wait = 4500) => { await p.goto(`${BASE}/web/#/${hash}`); await p.reload(); await p.waitForTimeout(wait); };
const jeStandIn = async () => {
  if (!flags.includes('--je')) return;
  await p.evaluate(() => {
    const bar = document.querySelector('header.MuiAppBar-root');
    if (bar && !bar.querySelector('.je-header-actions-row')) {
      const row = document.createElement('div');
      row.className = 'je-header-actions-row';
      row.textContent = 'JE';
      bar.appendChild(row);
    }
  });
};
const V = {
  async home() { await go('home'); await jeStandIn(); },
  async library() { await go(`movies?topParentId=${ctx.views.Movies}&collectionType=movies`, 5500); },
  async detail() { await go(`details?id=${ctx.by[process.env.DETAIL_ITEM || 'Lantern Harbor']}`, 5500); },
  async focus() {
    await go('home', 5000);
    // keyboard modality first, so :focus-visible and (TV layout) .show-focus apply, then focus a Continue Watching card
    await p.keyboard.press('Tab');
    // desktop layout: the card's link takes focus; TV layout: the .card itself (tabindex) and arrow keys move it
    await p.evaluate(() => { const l = document.querySelectorAll('.section1 .card a.cardContent'); const c = document.querySelectorAll('.section1 .card'); (document.documentElement.classList.contains('layout-tv') ? c[0] : l[1])?.focus(); });
    if (await p.evaluate(() => document.documentElement.classList.contains('layout-tv'))) await p.keyboard.press('ArrowRight');
    await p.waitForTimeout(900);
  },
};
for (const layout of layouts.split(',')) {
  await p.evaluate(([l]) => { if (l === 'tv') localStorage.setItem('layout', 'tv'); else localStorage.removeItem('layout'); }, [layout]);
  for (const k of (only ? only.split(',') : Object.keys(V))) {
    try { await V[k](); await p.screenshot({ path: `${outDir}/${k}-${layout}.png` }); console.log('ok', layout, k); } catch (e) { console.log('FAIL', layout, k, String(e).split('\n')[0]); }
  }
}
await b.close();
