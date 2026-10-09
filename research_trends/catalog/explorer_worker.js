/* Browser-side CSV index search. All source text is returned as data, never HTML. */
let manifest = null;
let columns = {};
let records = [];
let filtered = [];
const pageSize = 50;

const field = (row, name) => row[columns[name]] || "";
const splitIds = value => value ? value.split("|").filter(Boolean) : [];

function safeCell(value) {
  let text = String(value ?? "");
  if (/^[\s\u0000-\u001f]*[=+\-@]/u.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

async function load(url) {
  const base = new URL(url);
  const metaResponse = await fetch(base);
  if (!metaResponse.ok) throw new Error(`清单请求失败：HTTP ${metaResponse.status}`);
  manifest = await metaResponse.json();
  columns = Object.fromEntries(manifest.columns.map((name, index) => [name, index]));
  const dataResponse = await fetch(new URL(manifest.data_file, base));
  if (!dataResponse.ok) throw new Error(`索引请求失败：HTTP ${dataResponse.status}`);
  if (typeof DecompressionStream === "undefined") {
    throw new Error("此浏览器不支持流式 gzip 解压；请使用新版 Chrome、Edge 或下载完整 CSV。");
  }
  const stream = dataResponse.body.pipeThrough(new DecompressionStream("gzip"))
    .pipeThrough(new TextDecoderStream());
  const reader = stream.getReader();
  let tail = "";
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    const lines = (tail + value).split("\n");
    tail = lines.pop();
    for (const line of lines) if (line) records.push(JSON.parse(line));
    if (records.length % 10000 < lines.length) {
      postMessage({type: "progress", rows: records.length});
    }
  }
  if (tail.trim()) records.push(JSON.parse(tail));
  if (records.length !== manifest.row_count) {
    throw new Error(`索引行数不符：${records.length}/${manifest.row_count}`);
  }
  records.sort((a, b) => Number(field(b, "conference_year")) - Number(field(a, "conference_year"))
    || field(a, "venue").localeCompare(field(b, "venue"))
    || field(a, "title").localeCompare(field(b, "title")));
  filtered = records.map((_, index) => index);
  postMessage({type: "ready", manifest: {...manifest, taxonomy: manifest.taxonomy || null}});
}

function matches(row, f) {
  if (!f.includeProvisional && field(row, "record_status") === "provisional") return false;
  const venue = field(row, "venue");
  const year = Number(field(row, "conference_year"));
  if (f.venues?.length && !f.venues.includes(venue)) return false;
  if (f.yearMin && year < Number(f.yearMin)) return false;
  if (f.yearMax && year > Number(f.yearMax)) return false;
  if (f.statuses?.length && !f.statuses.includes(field(row, "classification_status"))) return false;
  if (f.countries?.length && !f.countries.some(country =>
    field(row, "affiliation_countries").split(";").map(x => x.trim()).includes(country))) return false;
  if (f.categoryIds?.length) {
    const ids = splitIds(field(row, "category_ids"));
    if (!f.categoryIds.some(id => ids.includes(id))) return false;
  }
  if (f.query) {
    const haystack = ["title", "authors", "paper_affiliations", "profile_institutions_unverified",
      "source_record_id", "venue", "doi_reported"].map(name => field(row, name)).join(" ").toLocaleLowerCase();
    if (!f.query.toLocaleLowerCase().trim().split(/\s+/u).every(term => haystack.includes(term))) return false;
  }
  return true;
}

function sortFiltered(mode) {
  if (mode === "citations") filtered.sort((ia, ib) => {
    const a = field(records[ia], "citation_count"), b = field(records[ib], "citation_count");
    if (a === "" && b !== "") return 1;
    if (b === "" && a !== "") return -1;
    return Number(b) - Number(a) || Number(field(records[ib], "conference_year")) - Number(field(records[ia], "conference_year"));
  });
  else if (mode === "title") filtered.sort((ia, ib) =>
    field(records[ia], "title").localeCompare(field(records[ib], "title")));
  else filtered.sort((ia, ib) => Number(field(records[ib], "conference_year")) - Number(field(records[ia], "conference_year"))
    || field(records[ia], "venue").localeCompare(field(records[ib], "venue")));
}

function page(number) {
  const start = Math.max(0, Number(number) || 0) * pageSize;
  return filtered.slice(start, start + pageSize).map(index => records[index]);
}

function summary() {
  const venues = new Map();
  const years = new Map();
  const status = new Map();
  const works = new Set();
  const cross = new Map();
  const l1 = new Set((manifest.taxonomy?.nodes || []).filter(node => node.level === 1).map(node => node.id));
  for (const index of filtered) {
    const row = records[index];
    const venue = field(row, "venue");
    const year = field(row, "conference_year");
    const state = field(row, "classification_status");
    works.add(field(row, "work_uid"));
    venues.set(venue, (venues.get(venue) || 0) + 1);
    years.set(year, (years.get(year) || 0) + 1);
    status.set(state, (status.get(state) || 0) + 1);
    const layers = splitIds(field(row, "category_ids")).filter(id => l1.has(id));
    if (!layers.length) layers.push("未分类／范围外");
    for (const layer of new Set(layers)) {
      const key = `${venue}\t${year}\t${layer}`;
      cross.set(key, (cross.get(key) || 0) + 1);
    }
  }
  return {rows: filtered.length, distinctWorks: works.size,
    venues: Object.fromEntries(venues), years: Object.fromEntries(years),
    statuses: Object.fromEntries(status),
    cross: [...cross].map(([key, count]) => [...key.split("\t"), count])
      .sort((a, b) => Number(b[1]) - Number(a[1]) || a[0].localeCompare(b[0]) || a[2].localeCompare(b[2]))};
}

function exportCsv() {
  const names = ["paper_uid", "venue", "conference_year", "title", "paper_url", "authors",
    "paper_affiliations", "affiliation_countries", "category_paths", "classification_status",
    "classification_evidence", "source_record_id"];
  const lines = [names.map(safeCell).join(",")];
  for (const index of filtered) lines.push(names.map(name => safeCell(field(records[index], name))).join(","));
  postMessage({type: "export", csv: "\ufeff" + lines.join("\r\n") + "\r\n", rows: filtered.length});
}

self.onmessage = async event => {
  try {
    const message = event.data;
    if (message.type === "init") await load(message.manifestUrl);
    if (message.type === "filter") {
      filtered = [];
      for (let i = 0; i < records.length; i++) if (matches(records[i], message.filters)) filtered.push(i);
      sortFiltered(message.filters.sort);
      postMessage({type: "result", page: 0, rows: page(0), summary: summary()});
    }
    if (message.type === "page") postMessage({type: "page", page: message.page, rows: page(message.page)});
    if (message.type === "export") exportCsv();
  } catch (error) {
    postMessage({type: "error", message: String(error?.message || error)});
  }
};
