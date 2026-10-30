import { cp, mkdir, rm } from "node:fs/promises";

const output = new URL("../dist/extension/", import.meta.url);
const source = new URL("../extension/", import.meta.url);
const marked = new URL("../node_modules/marked/lib/marked.esm.js", import.meta.url);
const purify = new URL("../node_modules/dompurify/dist/purify.es.mjs", import.meta.url);

await rm(output, { recursive: true, force: true });
await cp(source, output, { recursive: true });
await mkdir(new URL("vendor/", output), { recursive: true });
await cp(marked, new URL("vendor/marked.esm.js", output));
await cp(purify, new URL("vendor/purify.es.mjs", output));
