// Targeted runtime checks on the throwaway server. Prints JSON lines.
//   node qa/checks.mjs <system|import|tv|disable|routes> [out dir]
import fs from 'fs';
import { launch, login, BASE, setBrandingCss, items } from './lib.mjs';

const [, , what, outDir = '/tmp/fc-jf/checks'] = process.argv;
fs.mkdirSync(outDir, { recursive: true });
const css = (n) => fs.readFileSync(new URL(`../themes/flatcap-${n}.css`, import.meta.url), 'utf8');
const ctx = await items();
const out = (o) => console.log(JSON.stringify(o));
const theme = (p, t) => p.evaluate(([u, t]) => { localStorage.setItem(`${u}-appTheme`, t); localStorage.setItem(`${u}-dashboardTheme`, t); }, [ctx.uid, t]);
const rootInfo = (p) => p.evaluate(() => {
  const cs = getComputedStyle(document.documentElement);
  return { canvas: cs.getPropertyValue('--fc-canvas'), accent: cs.getPropertyValue('--jf-palette-primary-main'), bodyBg: getComputedStyle(document.body).backgroundColor,
    htmlBg: cs.backgroundColor, font: cs.fontFamily.slice(0, 60), plex: document.fonts.check('16px "IBM Plex Sans"'), dataTheme: document.documentElement.dataset.theme };
});

if (what === 'system') {
  await setBrandingCss(css('system'));
  for (const scheme of ['light', 'dark']) {
    const { b, p } = await launch({ scheme }); await login(p); await theme(p, 'dark');
    await p.goto(`${BASE}/web/#/home`); await p.reload(); await p.waitForTimeout(4500);
    await p.screenshot({ path: `${outDir}/system-${scheme}.png` }); out({ scheme, ...(await rootInfo(p)) }); await b.close();
  }
}

if (what === 'import') {
  await setBrandingCss('@import url("https://raw.githubusercontent.com/jellyfin/jellyfin-web/master/package.json");\n:root{--fc-import-probe:1}');
  const { b, p } = await launch(); const msgs = [];
  p.on('console', (m) => msgs.push(m.text().slice(0, 200)));
  p.on('response', (r) => { if (r.url().includes('raw.githubusercontent')) msgs.push(`RESPONSE ${r.status()} ${r.headers()['content-type']} nosniff=${r.headers()['x-content-type-options']}`); });
  await login(p); await p.goto(`${BASE}/web/#/home`); await p.waitForTimeout(5000);
  const url = 'https://raw.githubusercontent.com/jellyfin/jellyfin-web/master/package.json';
  out({ linkTest: await p.evaluate((u) => new Promise((res) => { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = u; l.onload = () => res('loaded'); l.onerror = () => res('blocked (onerror)'); document.head.appendChild(l); setTimeout(() => res('timeout'), 15000); }), url) });
  out({ importMsgs: msgs.filter((m) => /raw\.github|MIME|RESPONSE|stylesheet/i.test(m)),
    probeStyleApplied: await p.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--fc-import-probe')),
    cspMeta: await p.evaluate(() => !!document.querySelector('meta[http-equiv="Content-Security-Policy"]')) });
  await b.close();
}

if (what === 'disable') {
  await setBrandingCss(css('slate'));
  const { b, p } = await launch(); await login(p);
  await p.goto(`${BASE}/web/#/mypreferencesdisplay?userId=${ctx.uid}`); await p.waitForTimeout(6000);
  const txt = await p.evaluate(() => document.body.innerText);
  out({ mentionsCustomCss: txt.split('\n').filter((l) => /css/i.test(l)).slice(0, 6) });
  await p.evaluate((u) => localStorage.setItem(`${u}-disableCustomCss`, 'true'), ctx.uid);
  await p.reload(); await p.waitForTimeout(4500); out({ afterDisable: await rootInfo(p) });
  await p.evaluate((u) => localStorage.removeItem(`${u}-disableCustomCss`), ctx.uid); await b.close();
}

if (what === 'tv') {
  for (const mode of ['slate', 'daylight']) {
    await setBrandingCss(css(mode));
    const { b, p } = await launch({ scheme: mode === 'slate' ? 'dark' : 'light' }); await login(p);
    await p.evaluate(() => localStorage.setItem('layout', 'tv')); await theme(p, 'dark');
    await p.goto(`${BASE}/web/#/movies?topParentId=${ctx.views.Movies}&collectionType=movies`); await p.reload(); await p.waitForTimeout(6000);
    const layout = await p.evaluate(() => document.documentElement.className);
    const seq = [];
    for (let i = 0; i < 4; i++) {
      await p.keyboard.press(i === 0 ? 'Tab' : 'ArrowRight'); await p.waitForTimeout(500);
      seq.push(await p.evaluate(() => {
        const a = document.activeElement; const card = a.closest('.card'); const t = card ? card.querySelector('.cardBox') : a;
        const cs = getComputedStyle(t), ca = getComputedStyle(a);
        return { el: a.tagName + '.' + String(a.className).slice(0, 50), border: cs.borderTopColor, bw: cs.borderTopWidth, outline: ca.outlineColor, ow: ca.outlineWidth, os: ca.outlineStyle, bg: ca.backgroundColor };
      }));
    }
    await p.screenshot({ path: `${outDir}/tv-focus-${mode}.png` });
    out({ mode, layoutTv: /layout-tv/.test(layout), seq }); await b.close();
  }
}

if (what === 'routes') {
  await setBrandingCss(css('slate'));
  const { b, p } = await launch(); await login(p);
  const r = {};
  for (const h of ['home', 'search', 'movies?topParentId=' + ctx.views.Movies, 'details?id=' + ctx.by['Lantern Harbor'], `mypreferencesdisplay?userId=${ctx.uid}`, 'dashboard', 'dashboard/branding', 'dashboard/users', 'dashboard/libraries', 'dashboard/playback/transcoding']) {
    await p.goto(`${BASE}/web/#/${h}`); await p.waitForTimeout(3500);
    r[h.split('?')[0]] = await p.evaluate(() => [...document.querySelectorAll('style')].some((s) => s.textContent.includes('--fc-canvas')));
  }
  out({ customCssStylePresent: r }); await b.close();
}
