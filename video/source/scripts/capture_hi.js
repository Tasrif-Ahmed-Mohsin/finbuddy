// Sharp stills of the live Bluefin web app (390x844 @3x = 1170x2532) for the video, with tap targets.
// Usage: node capture_hi.js <outDir>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const MODE = process.argv[3] || 'local';  // local: the whole story on a local server; live: the proof pane on the live server
const URL = MODE === 'live' ? 'https://20-193-145-135.sslip.io' : 'http://localhost:8765';
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const out = path.resolve(process.argv[2]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const meta = {};

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, locale: 'en-US',
    userAgent: 'Mozilla/5.0 (Linux; Android 15; 23053RN02A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
  });
  const page = await context.newPage(); global.__page = page;
  page.on('dialog', (d) => d.accept());
  const cdp = await context.newCDPSession(page);
  await cdp.send('WebAuthn.enable', { enableUI: false });
  await cdp.send('WebAuthn.addVirtualAuthenticator', { options: {
    protocol: 'ctap2', transport: 'internal', hasResidentKey: true, hasUserVerification: true, isUserVerified: true,
    automaticPresenceSimulation: true } });

  const find = (text) => page.evaluate((txt) => {
    const el = [...document.querySelectorAll('[tabindex="0"],[role="button"]')].reverse()
      .find((e) => (e.innerText || '').trim().endsWith(txt) && e.getAttribute('aria-disabled') !== 'true');
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  }, text);
  const click = async (text) => {
    const box = await find(text);
    if (!box) throw new Error(`button not found: ${text}`);
    await sleep(250);
    const b2 = await find(text);
    await page.evaluate((txt) => {
      const el = [...document.querySelectorAll('[tabindex="0"],[role="button"]')].reverse()
        .find((e) => (e.innerText || '').trim().endsWith(txt) && e.getAttribute('aria-disabled') !== 'true');
      el.click();
    }, text);
    return b2;
  };
  const waitText = (txt, ms = 30000) => { console.log('wait', txt); return page.waitForFunction((t) => document.body.innerText.toLowerCase().includes(t.toLowerCase()), txt, { timeout: ms }); };
  const nextEnabled = (ms = 90000) => page.waitForFunction(() => {
    const el = [...document.querySelectorAll('[tabindex="0"],[role="button"]')].reverse().find((e) => (e.innerText || '').trim().endsWith('Next'));
    return el && el.getAttribute('aria-disabled') !== 'true';
  }, null, { timeout: ms });
  const scrollMain = (top) => page.evaluate((t) => {
    const els = [...document.querySelectorAll('div')].filter((d) => d.scrollHeight > d.clientHeight + 20 && /(auto|scroll)/.test(getComputedStyle(d).overflowY));
    const el = els.sort((a, b) => b.clientHeight - a.clientHeight)[0];
    if (el) el.scrollTo({ top: t === 'end' ? el.scrollHeight : t });
  }, top);
  const scrollTo = (txt) => page.evaluate((t) => {
    const el = [...document.querySelectorAll('div')].reverse().find((d) => d.innerText && d.innerText.trim().startsWith(t));
    if (el) el.scrollIntoView({ block: 'start' });
    return !!el;
  }, txt);
  const shot = async (name, extra = {}) => {
    await sleep(900);
    await page.screenshot({ path: path.join(out, `${name}.png`) });
    meta[name] = extra;
    console.log('shot', name);
  };

  await page.goto(URL, { waitUntil: 'networkidle' });
  await waitText('Next');
  await click('Next'); await sleep(600);
  await click('Next'); await sleep(600);
  await click('Use the AI'); await sleep(300);
  await click('Next'); await sleep(800);
  if (MODE === 'live') {
    await click('Go to the app'); await sleep(2500);
    await page.goto(`${URL}/family?pane=proof`, { waitUntil: 'networkidle' });
    await waitText('Anchored on FISCO BCOS', 30000);
    await shot('live_proof_top');
    for (const [n, t] of [['live_proof_log', '3 · BLACK BOX'], ['live_proof_fisco', 'FISCO BCOS 3.17.1']]) { await scrollTo(t); await shot(n); }
    fs.writeFileSync(path.join(out, 'shots_live.json'), JSON.stringify(meta, null, 1));
    await browser.close();
    return;
  }
  await click('Set up my key'); await sleep(2500);
  await click('Go to the app'); await sleep(1500);
  await waitText('days', 30000);
  await sleep(1500);
  await shot('home');
  await scrollMain(560); await shot('home_value');
  await scrollMain(0);

  await page.goto(`${URL}/story`, { waitUntil: 'networkidle' });
  await waitText('Start the story');
  await sleep(800);
  const steps = [
    ['start', 'Start the story (resets the sandbox)'],
    ['messages', "Forward this month's messages"],
    ['money', 'Check the money in China'],
    ['plan', 'Plan the year'],
    ['mandate', 'Turn it into a mandate'],
    ['sign', 'Sign as parent, then as student'],
    ['safety', 'Try both attacks'],
    ['shield', 'Add the approved job and sign the rule'],
    ['time', 'Fast-forward to 21 Feb 2027'],
    ['receipts', 'Show the receipts and books'],
    ['proof', 'Show the proof'],
  ];
  for (const [id, label] of steps) {
    await scrollMain(0);
    if (id === 'mandate') {
      const box = page.locator('textarea, input[type="text"]').first();
      await box.click(); await box.fill('');
      await page.keyboard.type('প্রতি মাসে ১ লাখ ২০ হাজার টাকা পর্যন্ত ছেলের চীনের অ্যাকাউন্টে পাঠাবে', { delay: 5 });
      await page.evaluate(() => document.activeElement && document.activeElement.blur());
    }
    const tap = await find(label);
    await scrollMain(0);
    await shot(`st_${id}_show`, { tap: await find(label) || tap });
    await click(label);
    if (id === 'proof') await waitText('Explore the app', 90000); else await nextEnabled();
    await sleep(600);
    await scrollMain('end');
    await shot(`st_${id}_result`);
    if (id !== 'proof') { await click('Next'); await sleep(900); }
  }

  await click('Explore the app'); await sleep(2500);
  await page.goto(`${URL}/family?pane=proof`, { waitUntil: 'networkidle' });
  await waitText('Anchored on FISCO BCOS', 30000);
  await shot('proof_top');
  for (const [n, t] of [['proof_receipts', '1 · YOUR MONEY'], ['proof_safety', '2 · SAFETY'], ['proof_log', '3 · BLACK BOX'], ['proof_fisco', 'FISCO BCOS 3.17.1']]) {
    await scrollTo(t); await shot(n);
  }
  await page.goto(`${URL}/plan`, { waitUntil: 'networkidle' }); await sleep(2000); await shot('plan_tab');
  await scrollMain(700); await shot('plan_tab2');

  await page.goto(`${URL}/judge`, { waitUntil: 'networkidle' });
  await waitText('Run all tasks');
  await shot('judge_top', { tap: await find('Run all tasks') });
  await click('Run all tasks');
  await waitText('20 of 20 tasks passed', 180000);
  await scrollMain(0);
  await shot('judge_result');
  await scrollMain(900); await shot('judge_list');

  fs.writeFileSync(path.join(out, 'shots.json'), JSON.stringify(meta, null, 1));
  await browser.close();
})().catch(async (e) => { console.error('FAILED', e.message); try { const pg = global.__page; console.error((await pg.evaluate(() => document.body.innerText)).slice(0, 1500)); await pg.screenshot({ path: 'fail.png' }); } catch (x) {} process.exit(1); });
