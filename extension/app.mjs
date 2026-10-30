import { marked } from "./vendor/marked.esm.js";
import DOMPurify from "./vendor/purify.es.mjs";

const host = "org.foxbook.lato";
const state = { directory: "", tabs: [], active: null };
const status = document.querySelector("#status");
const entries = document.querySelector("#entries");
const viewer = document.querySelector("#viewer");

function setStatus(message = "") { status.textContent = message; }
function childPath(base, name) { return base ? `${base}/${name}` : name; }
async function native(operation, relativePath) {
  const response = await browser.runtime.sendNativeMessage(host, { version: 1, request_id: crypto.randomUUID(), operation, relative_path: relativePath });
  if (!response?.ok) throw new Error(response?.error?.message || response?.error?.code || "Host通信に失敗しました。");
  return response.result;
}
async function loadDirectory(path) {
  try { setStatus(); const result = await native("list_directory", path); state.directory = path; renderBreadcrumbs(path); entries.replaceChildren(...result.entries.map((entry) => {
    const li = document.createElement("li"); const button = document.createElement("button"); button.replaceChildren(entryIcon(entry.kind), document.createTextNode(entry.name));
    button.onclick = () => entry.kind === "directory" ? loadDirectory(childPath(path, entry.name)) : openDocument(childPath(path, entry.name)); li.append(button); return li;
  })); } catch (error) { setStatus(error.message); }
}
function resolveLink(base, href) {
  if (href.startsWith("#")) return { path: base, anchor: href.slice(1) };
  const url = new URL(href, `https://lato.invalid/${base.split("/").slice(0, -1).join("/")}/`);
  if (url.origin !== "https://lato.invalid" || !url.pathname.endsWith(".md")) return null;
  return { path: decodeURIComponent(url.pathname.slice(1)), anchor: url.hash.slice(1) };
}
function entryIcon(type) { const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"), path = document.createElementNS("http://www.w3.org/2000/svg", "path"); svg.classList.add("entry-icon"); svg.setAttribute("viewBox", "0 0 24 24"); path.setAttribute("d", type === "directory" ? "M3.5 6.5h6l2 2h9v9.75A2.25 2.25 0 0 1 18.25 20.5h-14A2.25 2.25 0 0 1 2 18.25v-9.5A2.25 2.25 0 0 1 4.25 6.5Z" : "M6.5 2.75h7l4 4v14.5H6.5A2.25 2.25 0 0 1 4.25 19V5A2.25 2.25 0 0 1 6.5 2.75Zm6.5.5v4h4"); svg.append(path); return svg; }
function renderBreadcrumbs(path) { const root = document.querySelector("#breadcrumbs"), parts = path ? path.split("/") : []; root.replaceChildren(); const up = document.createElement("button"); up.textContent = "../"; up.onclick = () => loadDirectory(parts.slice(0, -1).join("/")); root.append(up); [["LATOルート", ""], ...parts.map((part, index) => [`› ${part}`, parts.slice(0, index + 1).join("/")])].forEach(([label, target]) => { const button = document.createElement("button"); button.textContent = label; button.onclick = () => loadDirectory(target); root.append(button); }); }
function renderTabs() { const root = document.querySelector("#tabs"); root.replaceChildren(...state.tabs.map((tab) => { const wrap = document.createElement("div"), open = document.createElement("button"), more = document.createElement("button"); wrap.className = `tab${tab.path === state.active ? " active" : ""}`; open.className = "tab-open"; open.textContent = tab.path.split("/").pop(); open.onclick = () => showDocument(tab.path); more.className = "more"; more.textContent = "︙"; more.setAttribute("aria-label", `${open.textContent} のメニュー`); more.onclick = () => { state.menuPath = tab.path; document.querySelector("#tab-menu-title").textContent = open.textContent; document.querySelector("#tab-menu").showModal(); }; wrap.append(open, more); return wrap; })); }
async function copyText(value) { try { await navigator.clipboard.writeText(value); setStatus("コピーしました。"); } catch { setStatus("コピーに失敗しました。"); } }
function showDocument(path, anchor = "") { const tab = state.tabs.find((item) => item.path === path); if (!tab) return; state.active = path; viewer.innerHTML = DOMPurify.sanitize(marked.parse(tab.content, { html: false }));
  viewer.querySelectorAll("a").forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); const target = resolveLink(path, link.getAttribute("href") || ""); if (!target) return setStatus("外部リンクはLATOでは開けません。"); target.path === path ? showDocument(path, target.anchor) : openDocument(target.path, target.anchor); }));
  renderTabs(); if (anchor) document.getElementById(anchor)?.scrollIntoView(); }
async function openDocument(path, anchor = "") { const existing = state.tabs.find((tab) => tab.path === path); if (existing) return showDocument(path, anchor); if (state.tabs.length >= 8) return setStatus("開ける文書は8件までです。");
  try { setStatus(); const result = await native("read_markdown", path); state.tabs.push({ path, content: result.content, pathInfo: result.path_info }); showDocument(path, anchor); } catch (error) { setStatus(error.message); } }
document.querySelector("#up").onclick = () => loadDirectory(state.directory.split("/").slice(0, -1).join("/"));
document.querySelector("#close-tab").onclick = () => { const path = state.menuPath, index = state.tabs.findIndex((tab) => tab.path === path); if (index >= 0) state.tabs.splice(index, 1); state.active = state.tabs[index - 1]?.path || state.tabs[0]?.path || null; document.querySelector("#tab-menu").close(); state.active ? showDocument(state.active) : viewer.replaceChildren(Object.assign(document.createElement("p"), { textContent: "フォルダからMarkdownを選択してください。" })); renderTabs(); };
[["#copy-file", "absolute_path"], ["#copy-parent", "parent_absolute_path"], ["#copy-name", "file_name"]].forEach(([selector, key]) => { document.querySelector(selector).onclick = () => { const tab = state.tabs.find((item) => item.path === state.menuPath); const value = key === "file_name" ? (tab?.pathInfo?.file_name || tab?.path.split("/").pop()) : tab?.pathInfo?.[key]; document.querySelector("#tab-menu").close(); copyText(value || ""); }; });
document.querySelector("#cancel-menu").onclick = () => document.querySelector("#tab-menu").close();
loadDirectory("");
