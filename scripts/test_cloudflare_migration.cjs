// Full browser regression uses an in-memory SQLite database and mocked providers.
// Every request is intercepted; it never writes to the user's database.
const { chromium } = require("playwright"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
const { setup, op } = require("../tests/helpers/cloudflare-fixture.cjs");
(async () => {
  const originalFetch = global.fetch;
  global.fetch = async (input) => {
    const url = String(input),
      expiry = "2026-11-20";
    if (url.includes("stock-options-chain"))
      return Response.json({
        result: {
          underlying_price: 28.5,
          options: [
            {
              symbol: "BBASW270",
              type: "PUT",
              expiration_date: expiry,
              strike: 27,
              last_price: 1.1,
              bid: 1,
              ask: 1.15,
              volume: 32000,
            },
            {
              symbol: "BBASK300",
              type: "CALL",
              expiration_date: expiry,
              strike: 30,
              last_price: 0.8,
              bid: 0.75,
              ask: 0.85,
              volume: 50000,
            },
          ],
        },
      });
    if (url.includes("stock-options/"))
      return Response.json({ trade_date: "2026-10-08" });
    if (url.includes("finance/chart"))
      return Response.json({
        chart: {
          result: [
            {
              meta: { regularMarketPrice: 28.5, regularMarketTime: 1791470000 },
              indicators: {
                quote: [
                  {
                    close: Array.from(
                      { length: 60 },
                      (_, i) => 27 + i * 0.02 + Math.sin(i) * 0.1,
                    ),
                  },
                ],
              },
            },
          ],
        },
      });
    throw Error("Unexpected external request in isolated test: " + url);
  };
  const browser = await chromium.launch({
    executablePath:
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
  });
  try {
    for (const viewport of [
      { width: 1440, height: 1000 },
      { width: 390, height: 844 },
    ]) {
      const { worker, env, call } = await setup();
      env.SLDX_API_TOKEN = "provider-fixture-only";
      const backup = JSON.parse(
        fs.readFileSync(
          path.join(
            __dirname,
            "../tmp/migration-2026-10-08/cloudflare-before.json",
          ),
          "utf8",
        ),
      );
      assert.equal((await call("/restore", backup)).status, 200);
      await call("/equities", {
        asset: "BBAS3",
        quantity: 100,
        average_price: 25,
        acquisition_date: "2026-08-01",
      });
      await call("/market/profiles", {
        profiles: [
          {
            asset: "BBAS3",
            assignment_eligible: true,
            long_term_suitable: true,
            quality_score: 0.88,
            data_confidence: 0.9,
            source: "fixture",
          },
        ],
      });
      env.ASSETS.fetch = async (request) => {
        const pathname = new URL(request.url || request).pathname;
        const filename = path.join(__dirname, "../static", pathname);
        if (!fs.existsSync(filename))
          return new Response("not found", { status: 404 });
        return new Response(fs.readFileSync(filename), {
          headers: {
            "Content-Type":
              filename.endsWith(".js") || filename.endsWith(".mjs")
                ? "text/javascript"
                : filename.endsWith(".css")
                  ? "text/css"
                  : "text/html",
          },
        });
      };
      const context = await browser.newContext({ viewport }),
        page = await context.newPage(),
        errors = [];
      page.on("console", (m) => {
        if (m.type() === "error") console.error("CONSOLE", m.text());
      });
      page.on("pageerror", (error) => {
        errors.push(error.message);
        console.error("PAGEERROR", error.message);
      });
      page.on("response", (r) => {
        if (r.status() >= 400) console.error("HTTP", r.status(), r.url());
      });
      await page.route("**/*", async (route) => {
        const r = route.request();
        if (new URL(r.url()).hostname !== "test.invalid") {
          await route.abort();
          return;
        }
        const response = await worker.fetch(
          new Request(r.url(), {
            method: r.method(),
            headers: r.headers(),
            ...(r.postData() ? { body: r.postData() } : {}),
          }),
          env,
        );
        await route.fulfill({
          status: response.status,
          headers: Object.fromEntries(response.headers),
          body: Buffer.from(await response.arrayBuffer()),
        });
      });
      await page.goto("https://test.invalid/faculdademaria/");
      await page.locator("[name=pin]").fill(env.ADMIN_PIN);
      await page.locator("#login-form button").click();
      await page
        .locator("#login")
        .waitFor({ state: "hidden" })
        .catch(async (e) => {
          console.error(
            "LOGIN",
            await page.locator("#login-error").textContent(),
          );
          throw e;
        });
      await page.waitForFunction(() =>
        document
          .querySelector("#market-message")
          .textContent.includes("SLDX disponível"),
      );
      assert.equal(await page.locator("#app").isVisible(), true);
      await page.locator("[data-open-quick-roi]").evaluate((el) => el.click());
      await page.locator("#quick-roi [name=strike]").fill("21,86");
      await page.locator("#quick-roi [name=premium]").fill("0,43");
      assert.match(
        await page.locator("#quick-roi-put-cost").textContent(),
        /21,43/,
      );
      assert.match(
        await page.locator("#quick-roi-call-value").textContent(),
        /22,29/,
      );
      const box = await page.locator("#quick-roi").boundingBox();
      assert.ok(box.width <= viewport.width && box.height <= viewport.height);
      await page.locator("#quick-roi [data-close-quick-roi]").last().click();
      for (const name of [
        "opportunities",
        "scanner",
        "jade",
        "roll",
        "tax",
        "open",
        "closed",
        "equity",
        "radar",
      ]) {
        await page
          .locator(`[data-screen=${name}]`)
          .first()
          .evaluate((el) => el.click());
        assert.equal(await page.locator(`#${name}-screen`).isVisible(), true);
        assert.ok(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
          name + " screen overflows viewport",
        );
      }
      await page
        .locator("[data-screen=opportunities]")
        .evaluate((el) => el.click());
      await page.locator("#market-symbols").fill("BBAS3");
      await page.locator("#market-refresh").click();
      await page.waitForFunction(() =>
        document
          .querySelector("#market-message")
          .textContent.includes("Mercado atualizado"),
      );
      assert.ok(
        (await page.locator("#opportunity-cards .migration-card").count()) > 0,
      );
      await page.locator("[data-screen=scanner]").evaluate((el) => el.click());
      assert.ok(
        (await page.locator("#scanner-cards .migration-card").count()) > 0,
      );
      await page
        .locator("[data-screen=tax]")
        .first()
        .evaluate((el) => el.click());
      assert.ok((await page.locator("#tax-month-rows tr").count()) > 0);
      assert.match(
        await page.locator("#tax-month-rows").textContent(),
        /Revisar exercício/,
      );
      assert.deepEqual(errors, []);
      await page.screenshot({
        path: path.join(
          __dirname,
          `../tmp/migration-2026-10-08/migration-tax-${viewport.width}.png`,
        ),
        fullPage: true,
      });
      console.log(
        `PASS ${viewport.width}px: login, ROI exercise prices, menu parity, real-data Radar flow, covered CALL scanner, tax memory, no JS errors`,
      );
      await context.close();
    }
  } finally {
    await browser.close();
    global.fetch = originalFetch;
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
