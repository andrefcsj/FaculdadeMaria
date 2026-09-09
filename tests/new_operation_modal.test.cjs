// Run with Playwright installed: node --test tests/new_operation_modal.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const trade = (equity = true) => ({trade_index: 0, option_code: equity ? 'LFTB11' : 'PETRT480',
  underlying_asset: equity ? 'LFTB11' : 'PETR4', side: 'Venda', market: equity ? 'VISTA' : 'OPCAO DE VENDA',
  event_type: equity ? 'equity_sale' : 'trade', quantity: equity ? 37 : 100, contracts: equity ? '0.37' : '1',
  unit_price: '56', gross_value: '2072', allocated_costs: '1.50', allocated_irrf: '0'});
const note = trades => ({note_number:'123', trade_date:'2026-09-09', net_cash:'2070.50', operational_costs:'1.50', trades});
const upload = page => page.locator('#newBrokerageNote').setInputFiles({name:'nota.pdf', mimeType:'application/pdf', buffer:Buffer.from('mock pdf')});

async function setup() {
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1200}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const scripts = ['date_fields.js', 'new_operation.js', 'brokerage_note_import.js', 'new_operation_note_lookup.js'];
  const html = '<!doctype html><html><head><style>'+fs.readFileSync(path.join(root,'static/new_operation.css'),'utf8')+'</style></head><body><button data-open-new-operation>Abrir</button>'+
    fs.readFileSync(path.join(root,'templates/components/new_operation_modal.html'),'utf8')+
    scripts.map(file => `<script>${fs.readFileSync(path.join(root,'static',file),'utf8')}</script>`).join('')+'</body></html>';
  await page.route('http://fm.test/**', route => route.fulfill({contentType:'text/html', body:html}));
  await page.route('**/api/carteira-acoes', route => route.fulfill({json:{ok:true, holdings:[]}}));
  await page.route('**/api/operacoes/preview', route => route.fulfill({json:{ok:true, exercise_probability:'--'}}));
  await page.goto('http://fm.test/testing');
  await page.locator('[data-open-new-operation]').click();
  return {browser,page,errors};
}

test('spot note hides option fields, uses units and submits without strike', async () => {
  const {browser,page,errors} = await setup();
  try {
    let lookups=0;
    await page.route('**/api/opcoes/**', route => {lookups++; return route.fulfill({json:{ok:true}})});
    await page.route('**/api/notas-corretagem/analisar', route => route.fulfill({json:{ok:true,note:note([trade()])}}));
    let saved;
    await page.route('**/api/operacoes', route => {saved=route.request().postDataJSON();return route.fulfill({json:{ok:true}})});
    await upload(page);
    await page.waitForFunction(() => document.querySelector('#newContracts').value === '37');
    assert.equal(await page.locator('#newStrike').isVisible(),false);
    assert.equal(await page.locator('#newExpiry').evaluate(el => el.required),false);
    assert.match(await page.locator('#newSummaryDetails').textContent(), /37 unidades/);
    await page.locator('#newOperationSave').click();
    await page.waitForFunction(() => document.querySelector('#newOperationModal').hidden);
    assert.equal(saved.Nota_corretagem.trade.event_type,'equity_sale');
    assert.equal(saved.Strike,'0');
    assert.equal(lookups,0);
    assert.deepEqual(errors,[]);
  } finally {await browser.close()}
});

test('all closing controls discard the note and restore a blank option form', async () => {
  const {browser,page,errors} = await setup();
  try {
    await page.route('**/api/notas-corretagem/analisar', route => route.fulfill({json:{ok:true,note:note([trade()])}}));
    for (const close of ['cancel','x','escape','backdrop']) {
      await upload(page);
      await page.waitForFunction(() => document.querySelector('#newContracts').value === '37');
      if(close==='escape') await page.keyboard.press('Escape');
      else if(close==='cancel') await page.locator('button[data-new-op-close]').last().click();
      else if(close==='x') await page.locator('button[data-new-op-close]').first().click();
      else await page.locator('.new-op-modal__backdrop').click({position:{x:2,y:2},force:true});
      await page.locator('[data-open-new-operation]').click();
      assert.equal(await page.locator('#newOptionCode').inputValue(),'');
      assert.equal(await page.locator('#newBrokerageNote').inputValue(),'');
      assert.equal(await page.locator('#brokerageImportResult').isVisible(),false);
      assert.equal(await page.locator('#newStrike').evaluate(el => el.required && !el.disabled),true);
      assert.equal(await page.evaluate(() => window.brokerageNoteImport.preparePayload({}).Nota_corretagem),undefined);
    }
    assert.deepEqual(errors,[]);
  } finally {await browser.close()}
});

test('a note analysis arriving after cancellation cannot restore its data', async () => {
  const {browser,page,errors} = await setup();
  try {
    let release, arrived;
    const gate = new Promise(resolve => {release=resolve});
    const started = new Promise(resolve => {arrived=resolve});
    await page.route('**/api/notas-corretagem/analisar', async route => {arrived();await gate;await route.fulfill({json:{ok:true,note:note([trade()])}})});
    await upload(page); await started;
    await page.locator('button[data-new-op-close]').last().click();
    await page.locator('[data-open-new-operation]').click();
    const done=page.waitForResponse('**/api/notas-corretagem/analisar'); release();await done;
    await page.waitForTimeout(50);
    assert.equal(await page.locator('#newOptionCode').inputValue(),'');
    assert.equal(await page.locator('#brokerageImportResult').isVisible(),false);
    assert.deepEqual(errors,[]);
  } finally {await browser.close()}
});

test('mixed note restores strike validation for the next option trade', async () => {
  const {browser,page,errors} = await setup();
  try {
    await page.route('**/api/notas-corretagem/analisar', route => route.fulfill({json:{ok:true,note:note([trade(),{...trade(false),trade_index:1}])}}));
    await page.route('**/api/opcoes/**', route => route.fulfill({json:{ok:true,asset:'PETR4',strike:48,expiry:'2026-09-18'}}));
    await page.route('**/api/operacoes', route => route.fulfill({json:{ok:true}}));
    await upload(page);
    await page.waitForFunction(() => document.querySelector('#newContracts').value === '37');
    await page.locator('#newOperationSave').click();
    await page.waitForFunction(() => document.querySelector('#newOptionCode').value === 'PETRT480');
    assert.equal(await page.locator('#newStrike').isVisible(),true);
    assert.equal(await page.locator('#newStrike').evaluate(el=>el.required && !el.disabled),true);
    assert.equal(await page.locator('#newContracts').inputValue(),'1');
    assert.match(await page.locator('#newOperationSave').textContent(),/2 de 2/);
    assert.deepEqual(errors,[]);
  } finally {await browser.close()}
});

test('an old option lookup cannot overwrite the same code in a new import', async () => {
  const {browser,page,errors} = await setup();
  try {
    let release, arrived, requests=0;
    const gate = new Promise(resolve => {release=resolve});
    const started = new Promise(resolve => {arrived=resolve});
    await page.route('**/api/notas-corretagem/analisar', route => route.fulfill({json:{ok:true,note:note([trade(false)])}}));
    await page.route('**/api/opcoes/**', async route => {
      const first = ++requests === 1;
      if(first) {arrived();await gate}
      await route.fulfill({json:{ok:true,asset:'PETR4',strike:first?99:48,expiry:'2026-09-18'}});
    });
    await upload(page);await started;
    await page.keyboard.press('Escape');
    await page.locator('[data-open-new-operation]').click();
    await upload(page);
    await page.waitForFunction(() => document.querySelector('#newStrike').value.includes('48,00'));
    const done=page.waitForResponse('**/api/opcoes/**');release();await done;
    await page.waitForTimeout(50);
    assert.match(await page.locator('#newStrike').inputValue(),/48,00/);
    assert.deepEqual(errors,[]);
  } finally {await browser.close()}
});
