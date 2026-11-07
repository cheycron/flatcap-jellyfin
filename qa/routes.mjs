import { launch, login, BASE, items } from './lib.mjs';
const { by, uid } = await items();
const { b, p } = await launch(); await login(p);
const has = () => p.evaluate(() => ({ hash: location.hash.slice(0, 40), fc: [...document.styleSheets].length, styleWithFc: [...document.querySelectorAll('style')].filter(s => s.textContent.includes('--fc-')).length, accent: getComputedStyle(document.documentElement).getPropertyValue('--jf-palette-primary-main'), theme: document.documentElement.dataset.theme }));
for (const h of ['home', 'dashboard', 'mypreferencesdisplay', `details?id=${by['Sintel']}`, 'dashboard/branding', 'dashboard/users']) { await p.goto(`${BASE}/web/#/${h}`); await p.waitForTimeout(3500); console.log(JSON.stringify(await has())); }
await p.goto(`${BASE}/web/#/details?id=${by['Sintel']}`); await p.waitForTimeout(3000); await p.click('.btnResume:visible, .btnPlay:visible'); await p.waitForTimeout(5000); console.log('player', JSON.stringify(await has()));
await b.close();
