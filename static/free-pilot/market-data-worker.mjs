import "./domain.js";
import "./market-data.js";
import { unzipSync } from "./vendor/fflate.mjs";
self.onmessage = ({ data }) => {
  try {
    const { kind, buffer, universe, year, asOf } = data;
    const files = unzipSync(new Uint8Array(buffer), {
      filter: (file) =>
        kind === "cvm"
          ? /DRE_con|BPA_con|BPP_con|DFC_MI_con/.test(file.name)
          : /\.txt$/i.test(file.name),
    });
    const result =
      kind === "cvm"
        ? FMMarketData.cvm(files, universe, year)
        : Object.values(files).flatMap((bytes) =>
            FMMarketData.cotahist(
              new TextDecoder("iso-8859-1").decode(bytes),
              universe,
              asOf,
            ),
          );
    self.postMessage({ ok: true, result });
  } catch (error) {
    self.postMessage({
      ok: false,
      error: error.message || "Arquivo da fonte inválido.",
    });
  }
};
