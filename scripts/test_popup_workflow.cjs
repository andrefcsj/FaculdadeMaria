// All financial writes in this browser regression go to in-memory SQLite.
const { chromium } = require("playwright"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
const { setup } = require("../tests/helpers/cloudflare-fixture.cjs");
const folder = path.join(__dirname, "../tmp/popup-2026-10-09");
// Create a searchable synthetic PDF and cache the app's pinned PDF.js assets.
fs.mkdirSync(folder, { recursive: true });
const lines = [
  "BTG PACTUAL NOTA DE CORRETAGEM 99000001",
  "09/10/2026",
  "1-BOVESPA V OPCAO DE VENDA 11/26 PETRW480 100 1,00 100,00 C",
  "1-BOVESPA V OPCAO DE VENDA 11/26 BBASW270 100 0,80 80,00 C",
  "TOTAL CORRETAGEM / DESPESAS 0,00",
];
const stream =
  "BT /F1 10 Tf 30 760 Td " +
  lines
    .map((line, i) => (i ? "0 -22 Td " : "") + "(" + line + ") Tj")
    .join(" ") +
  " ET";
const objects = [
  "<< /Type /Catalog /Pages 2 0 R >>",
  "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
  "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
  "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  "<< /Length " +
    Buffer.byteLength(stream) +
    " >>\nstream\n" +
    stream +
    "\nendstream",
];
let pdf = "%PDF-1.4\n",
  offsets = [0];
objects.forEach((object, i) => {
  offsets.push(Buffer.byteLength(pdf));
  pdf += i + 1 + " 0 obj\n" + object + "\nendobj\n";
});
const xref = Buffer.byteLength(pdf);
pdf +=
  "xref\n0 6\n0000000000 65535 f \n" +
  offsets
    .slice(1)
    .map((offset) => String(offset).padStart(10, "0") + " 00000 n \n")
    .join("") +
  "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" +
  xref +
  "\n%%EOF\n";
fs.writeFileSync(path.join(folder, "note-fixture.pdf"), pdf);
for (const file of ["pdf.min.mjs", "pdf.worker.min.mjs"]) {
  const target = path.join(folder, file);
  if (!fs.existsSync(target))
    require("node:child_process").execFileSync("curl", [
      "-fsS",
      "--max-time",
      "40",
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/" + file,
      "-o",
      target,
    ]);
}
(async () => {
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
      let failNextImport = false;
      env.ASSETS.fetch = async (input) => {
        const file = path.join(
          __dirname,
          "../static",
          new URL(input.url || input).pathname,
        );
        if (!fs.existsSync(file))
          return new Response("not found", { status: 404 });
        return new Response(fs.readFileSync(file), {
          headers: {
            "Content-Type":
              file.endsWith(".js") || file.endsWith(".mjs")
                ? "text/javascript"
                : file.endsWith(".css")
                  ? "text/css"
                  : "text/html",
          },
        });
      };
      const context = await browser.newContext({
          viewport,
          hasTouch: viewport.width === 390,
        }),
        page = await context.newPage(),
        errors = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await page.route("**/*", async (route) => {
        const r = route.request(),
          url = new URL(r.url());
        if (url.hostname === "cdnjs.cloudflare.com") {
          await route.fulfill({
            status: 200,
            headers: {
              "Content-Type": "text/javascript",
              "Access-Control-Allow-Origin": "*",
            },
            body: fs.readFileSync(
              path.join(folder, path.basename(url.pathname)),
            ),
          });
          return;
        }
        if (url.hostname !== "test.invalid") {
          await route.abort();
          return;
        }
        if (url.pathname.endsWith("/api/notes/import") && failNextImport) {
          failNextImport = false;
          await route.fulfill({
            status: 500,
            contentType: "application/json",
            body: JSON.stringify({
              error: "Falha isolada para testar nova tentativa.",
            }),
          });
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
      await page.locator("#app").waitFor({ state: "visible" });
      await page.waitForFunction(
        () =>
          window.FMDialogs && document.querySelector("#system-question-dialog"),
      );
      await page
        .locator("[data-screen=open]")
        .first()
        .evaluate((e) => e.click());
      await page.locator("#open-note-import").click();
      await page
        .locator("#note-import-dialog [name=pdf]")
        .setInputFiles(path.join(folder, "note-fixture.pdf"));
      await page.locator("#staged-note-trade").waitFor();
      assert.equal(await page.locator("#staged-note-trade option").count(), 2);
      await page.locator("#trigger-note-import").click();
      await page.waitForFunction(() =>
        document
          .querySelector(".staged-import-status")
          ?.textContent.includes("1 restante"),
      );
      assert.equal(
        await page.locator("#note-import-dialog").evaluate((e) => e.open),
        true,
      );
      assert.equal(
        (await (await call("/dashboard")).json()).operations.length,
        1,
      );
      failNextImport = true;
      await page.locator("#trigger-note-import").click();
      await page.waitForFunction(() =>
        document
          .querySelector("#note-import-dialog [data-note-result]")
          .classList.contains("is-error"),
      );
      assert.equal(
        await page.locator("#note-import-dialog").evaluate((e) => e.open),
        true,
      );
      assert.equal((await (await call("/dashboard")).json()).notes.length, 1);
      assert.equal(
        await page.locator("#newOptionCode").inputValue(),
        "BBASW270",
      );
      await page.locator("#trigger-note-import").click();
      await page.waitForFunction(
        () => !document.querySelector("#note-import-dialog").open,
      );
      assert.equal(await page.locator("#open-screen").isVisible(), true);
      let data = await (await call("/dashboard")).json();
      assert.equal(data.operations.length, 2);
      assert.equal(data.notes.length, 2);
      assert.equal(await page.locator("#newOptionCode").inputValue(), "");
      assert.equal(
        await page
          .locator("#note-import-dialog [name=pdf]")
          .evaluate((e) => e.files.length),
        0,
      );
      await page.locator("#open-note-import").click();
      assert.equal(await page.locator("#newOptionCode").inputValue(), "");
      await page.locator("[data-close-note-import]").first().click();
      // Failed parsing must leave the form open, with no new financial records.
      await page.locator("#open-note-import").click();
      await page.locator("#note-import-dialog [name=pdf]").setInputFiles({
        name: "invalid.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("not a PDF"),
      });
      await page.waitForFunction(() =>
        document
          .querySelector("#note-import-dialog [data-note-result]")
          .classList.contains("is-error"),
      );
      assert.equal(
        await page.locator("#note-import-dialog").evaluate((e) => e.open),
        true,
      );
      assert.equal((await (await call("/dashboard")).json()).notes.length, 2);
      await page.locator("[data-close-note-import]").first().click();
      const ids = await page
        .locator("dialog:not(#system-question-dialog),.ccx-dialog")
        .evaluateAll((es) => es.map((e) => e.id || e.parentElement.id));
      for (const id of ids) {
        const selector = id.endsWith("ComparatorModal")
          ? "#" + id + " .ccx-dialog"
          : "#" + id;
        await page.evaluate((id) => {
          const el = document.getElementById(id);
          if (el.tagName === "DIALOG") el.showModal();
          else {
            el.hidden = false;
            document.body.classList.add("ccx-open");
          }
        }, id);
        if (!id.endsWith("ComparatorModal"))
          assert.equal(
            await page
              .locator(selector)
              .evaluate(
                (e) => getComputedStyle(e, "::backdrop").backdropFilter,
              ),
            "none",
          );
        const header = page.locator(selector + " header").first();
        await header.waitFor({ state: "visible" });
        const start = await page.locator(selector).boundingBox(),
          handle = await header.boundingBox();
        const x = handle.x + Math.min(90, handle.width / 3),
          y = handle.y + Math.min(22, handle.height / 2);
        await page.mouse.move(x, y);
        await page.mouse.down();
        await page.mouse.move(x - 65, y + 60, { steps: 6 });
        await page.mouse.up();
        const moved = await page.locator(selector).boundingBox();
        assert.ok(
          moved.x < start.x - 20 || moved.y > start.y + 20,
          id + " did not move",
        );
        // A double click restores the centered position without changing form data.
        await header.dblclick({ position: { x: 90, y: 22 } });
        const centered = await page.locator(selector).boundingBox();
        assert.ok(
          Math.abs(centered.x - start.x) < 2 &&
            Math.abs(centered.y - start.y) < 2,
          id + " did not reset",
        );
        await page.evaluate((id) => {
          const el = document.getElementById(id);
          if (el.tagName === "DIALOG") el.close();
          else {
            el.hidden = true;
            document.body.classList.remove("ccx-open");
          }
        }, id);
      }
      await page.evaluate(() => {
        window.answerPromise = FMDialogs.prompt(
          "Valor de teste:",
          "25,50",
        ).then((v) => (window.answer = v));
      });
      await page
        .locator("#system-question-dialog")
        .waitFor({ state: "visible" });
      const questionBox = await page
        .locator("#system-question-dialog")
        .boundingBox();
      await page.mouse.move(questionBox.x + 90, questionBox.y + 22);
      await page.mouse.down();
      await page.mouse.move(questionBox.x + 30, questionBox.y + 80, {
        steps: 5,
      });
      await page.mouse.up();
      assert.ok(
        (await page.locator("#system-question-dialog").boundingBox()).y >
          questionBox.y + 20,
      );
      await page.locator("#system-question-dialog input").fill("31,25");
      await page.locator("#system-question-dialog button[type=submit]").click();
      await page.waitForFunction(() => window.answer === "31,25");
      await page.evaluate(() => {
        FMDialogs.confirm("Cancelar teste?").then(
          (v) => (window.cancelAnswer = v),
        );
      });
      await page.keyboard.press("Escape");
      await page.waitForFunction(() => window.cancelAnswer === false);
      if (viewport.width === 390) {
        await page.evaluate(() =>
          document.getElementById("quick-roi").showModal(),
        );
        const handle = await page.locator("#quick-roi header").boundingBox(),
          before = await page.locator("#quick-roi").boundingBox(),
          cdp = await context.newCDPSession(page);
        const point = { x: handle.x + 90, y: handle.y + 22 };
        await cdp.send("Input.dispatchTouchEvent", {
          type: "touchStart",
          touchPoints: [point],
        });
        await cdp.send("Input.dispatchTouchEvent", {
          type: "touchMove",
          touchPoints: [{ x: point.x - 35, y: point.y + 50 }],
        });
        await cdp.send("Input.dispatchTouchEvent", {
          type: "touchEnd",
          touchPoints: [],
        });
        assert.ok(
          (await page.locator("#quick-roi").boundingBox()).y > before.y + 20,
          "touch drag did not move",
        );
        await page.evaluate(() => document.getElementById("quick-roi").close());
        await cdp.detach();
      }
      assert.deepEqual(errors, []);
      await page.screenshot({
        path: path.join(folder, "popup-workflow-" + viewport.width + ".png"),
        fullPage: true,
      });
      console.log(
        `PASS ${viewport.width}px: actual two-trade PDF, keep open until last, close/reset/navigate, error stays open, ${ids.length + 1} draggable popups, prompt/confirmation semantics, no JS errors`,
      );
      await context.close();
    }
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
