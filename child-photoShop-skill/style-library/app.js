/* 界面层：把 profile-library.js 的纯逻辑接到 DOM 上。
 *
 * 这里只做三件事：把风格画成卡片、把滑块的变化换算成混合结果、把结果导出成文件。
 * 所有算数都在 profile-library.js 里，本文件不重复实现任何混合规则。
 *
 * 不引入任何第三方依赖，也不发任何网络请求：风格库是内置的，保存接口是占位的。
 */
(function () {
  "use strict";

  var lib = window.StyleLibrary;

  /* 默认配比：七分奶油暖白 + 三分韩系清透。选这个不是因为它最好看，而是因为它一打开
   * 就能看出「权重是真的生效」——换成均分的话，界面上第一次看到的结果和「随便选选」
   * 没有区别，加权混合这件事本身就白做了。 */
  var DEFAULT_WEIGHTS = {
    "cream-white": 70,
    "korean-clear": 30,
    "forest-green": 0,
    "sunset-camp": 0,
    "french-vintage": 0
  };

  var PLACEHOLDER_NOTE = "保存接口为占位实现，未接入后端，未落盘。";

  var library = [];
  var weights = {};
  var current = null;
  var nodes = {};

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined && text !== null) {
      node.textContent = String(text);
    }
    return node;
  }

  /* 量纲差别很大：颗粒 0.008、肤色冷暖 20.0。统一四位小数会让大数变成 20.0000，
   * 统一两位小数会让颗粒归零成 0.01。按量级分档是唯一能一张表看全的办法。 */
  function formatNumber(value) {
    if (typeof value !== "number" || !isFinite(value)) {
      return "—";
    }
    var abs = Math.abs(value);
    if (abs >= 10) {
      return value.toFixed(2);
    }
    if (abs >= 1) {
      return value.toFixed(3);
    }
    return value.toFixed(4);
  }

  function percent(weight) {
    return Math.round(weight * 100) + "%";
  }

  function defaultWeights() {
    var out = {};
    library.forEach(function (profile) {
      var preset = DEFAULT_WEIGHTS[profile.id];
      out[profile.id] = typeof preset === "number" ? preset : 0;
    });
    return out;
  }

  function totalWeight() {
    return library.reduce(function (acc, profile) {
      return acc + (weights[profile.id] || 0);
    }, 0);
  }

  /* 始终传入全部风格（包括权重为 0 的），由 normaliseWeights 统一处理：
   * 有权重的按比归一化、全为 0 的走均分。若在界面层先把 0 的过滤掉，
   * 「全部拖到 0」就变成空输入报错，而不是一个合理结果。 */
  function entries() {
    return library.map(function (profile) {
      return { profile: profile, weight: weights[profile.id] || 0 };
    });
  }

  function swatch(label, hex) {
    var wrap = el("div", "swatch");
    var chip = el("span", "chip");
    chip.style.backgroundColor = hex;
    chip.title = String(hex);
    wrap.appendChild(chip);
    wrap.appendChild(el("span", null, label + " " + hex));
    return wrap;
  }

  function buildCard(profile) {
    var card = el("div", "card");

    var head = el("div", "card-head");
    head.appendChild(el("h3", null, profile.name));
    head.appendChild(el("span", "card-role", "参考角色 " + (profile.role || "color")));
    card.appendChild(head);

    var mood = (profile.mood || []).join(" · ");
    card.appendChild(el("p", "mood", mood || "—"));

    var swatches = el("div", "swatches");
    swatches.appendChild(swatch("肤色", (profile.skin || {}).tone_hex));
    swatches.appendChild(swatch("背景", (profile.background || {}).tone_hex));
    card.appendChild(swatches);

    var row = el("div", "weight-row");
    row.appendChild(el("span", "weight-label", "权重"));
    var slider = el("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.step = "1";
    slider.value = String(weights[profile.id] || 0);
    slider.setAttribute("aria-label", profile.name + " 权重");
    var readout = el("span", "weight-value", (weights[profile.id] || 0) + "%");
    slider.addEventListener("input", function () {
      weights[profile.id] = Number(slider.value);
      readout.textContent = weights[profile.id] + "%";
      card.classList.toggle("is-active", weights[profile.id] > 0);
      recompute();
    });
    row.appendChild(slider);
    row.appendChild(readout);
    card.appendChild(row);

    if ((weights[profile.id] || 0) > 0) {
      card.classList.add("is-active");
    }
    return card;
  }

  function renderLibrary() {
    nodes.library.innerHTML = "";
    library.forEach(function (profile) {
      nodes.library.appendChild(buildCard(profile));
    });
  }

  function renderFormula(mixed) {
    var formula = el("div", "formula");
    var parts = (mixed.source && mixed.source.mixedFrom ? mixed.source.mixedFrom : [])
      .filter(function (item) { return item.weight > 0.0001; });
    if (!parts.length) {
      formula.appendChild(el("span", "formula-chip", "无有效配比"));
      return formula;
    }
    parts.forEach(function (item) {
      formula.appendChild(el("span", "formula-chip", item.name + " " + percent(item.weight)));
    });
    return formula;
  }

  function renderDimTable(mixed) {
    var table = el("table", "dim-table");
    var thead = el("thead");
    var headRow = el("tr");
    headRow.appendChild(el("th", null, "维度"));
    headRow.appendChild(el("th", null, "混合值"));
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = el("tbody");
    lib.summarise(mixed).forEach(function (row) {
      var tr = el("tr");
      tr.appendChild(el("td", null, row.label));
      tr.appendChild(el("td", "num", formatNumber(row.value)));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
  }

  function renderResult(mixed) {
    var body = nodes.result;
    body.innerHTML = "";
    body.appendChild(el("p", "result-name", mixed.name));
    body.appendChild(renderFormula(mixed));

    var swatches = el("div", "swatches");
    swatches.appendChild(swatch("混合肤色", (mixed.skin || {}).tone_hex));
    swatches.appendChild(swatch("混合背景", (mixed.background || {}).tone_hex));
    body.appendChild(swatches);

    if (totalWeight() === 0) {
      body.appendChild(el("p", "mood", "全部权重为 0，按均分处理。"));
    }
    body.appendChild(renderDimTable(mixed));
  }

  function renderError(message) {
    nodes.result.innerHTML = "";
    nodes.result.appendChild(el("div", "error", "混合失败：" + message));
  }

  function setStatus(message, isError) {
    nodes.status.textContent = message;
    nodes.status.style.color = isError ? "var(--danger)" : "var(--text-muted)";
  }

  function recompute() {
    try {
      current = lib.mixProfiles(entries());
    } catch (error) {
      current = null;
      nodes.exportBtn.disabled = true;
      renderError(error.message);
      setStatus("混合失败：" + error.message, true);
      return;
    }
    renderResult(current);
    nodes.exportBtn.disabled = false;
  }

  function timestamp() {
    var now = new Date();
    function pad(value) {
      return String(value).padStart(2, "0");
    }
    return [
      now.getFullYear(),
      pad(now.getMonth() + 1),
      pad(now.getDate()),
      "-",
      pad(now.getHours()),
      pad(now.getMinutes())
    ].join("");
  }

  function download(text, filename) {
    var blob = new Blob([text], { type: "application/json;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = el("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function onExport() {
    if (!current) {
      setStatus("还没有可导出的混合结果。", true);
      return;
    }
    try {
      var saved = lib.saveStyle(current);
      var text = lib.exportProfile(current);
      var filename = "style-profile-" + timestamp() + ".json";
      download(text, filename);
      setStatus("已导出 " + filename + "。" + (saved.persisted ? "" : PLACEHOLDER_NOTE), false);
    } catch (error) {
      setStatus("导出失败：" + error.message, true);
    }
  }

  function onReset() {
    weights = defaultWeights();
    renderLibrary();
    recompute();
    setStatus("已恢复默认配比：" + (current ? current.name : "") + "。" + PLACEHOLDER_NOTE, false);
  }

  function init() {
    nodes.library = document.getElementById("library-list");
    nodes.result = document.getElementById("result-body");
    nodes.status = document.getElementById("status");
    nodes.exportBtn = document.getElementById("export-btn");
    nodes.resetBtn = document.getElementById("reset-btn");

    if (!nodes.library || !nodes.result || !nodes.status || !nodes.exportBtn || !nodes.resetBtn) {
      return;
    }
    if (!lib) {
      renderError("未能加载 profile-library.js");
      return;
    }

    library = lib.loadStyleLibrary();
    weights = defaultWeights();

    nodes.exportBtn.addEventListener("click", onExport);
    nodes.resetBtn.addEventListener("click", onReset);

    renderLibrary();
    recompute();
    setStatus("风格库为内置静态数据。" + PLACEHOLDER_NOTE, false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
