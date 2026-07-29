const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

const [,, inFile, outFile, scaleArg] = process.argv;
const scale = parseFloat(scaleArg || '2');
const border = 10;
const WEBAPP = path.join(__dirname, 'drawio_app/drawio/src/main/webapp');

(async () => {
  const xml = fs.readFileSync(inFile, 'utf8');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1200, deviceScaleFactor: scale });
  await page.goto('file://' + path.join(WEBAPP, 'export3.html'), { waitUntil: 'networkidle0' });

  await page.evaluate((data) => { render(data); },
    { xml, format: 'png', scale: 1, border, bg: '#ffffff', w: 0, h: 0 });

  await page.waitForSelector('#LoadingComplete', { timeout: 120000 });
  const boundsStr = await page.$eval('#LoadingComplete', el => el.getAttribute('bounds'));
  const b = JSON.parse(boundsStr);
  const W = Math.ceil(b.width) + 2 * border;
  const H = Math.ceil(b.height) + 2 * border;
  await page.setViewport({ width: W, height: H, deviceScaleFactor: scale });
  await new Promise(r => setTimeout(r, 400));
  await page.screenshot({ path: outFile, clip: { x: 0, y: 0, width: W, height: H }, omitBackground: false });
  await browser.close();
  console.log(`OK ${outFile}  ${Math.round(W*scale)}x${Math.round(H*scale)} px (bounds ${Math.round(b.width)}x${Math.round(b.height)})`);
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
