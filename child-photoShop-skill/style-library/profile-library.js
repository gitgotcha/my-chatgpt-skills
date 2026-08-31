/* 风格画像库：纯逻辑层。
 *
 * 这里刻意不碰 DOM，也不碰任何浏览器 API —— 所有函数都是「输入数据 → 输出数据」，
 * 因此 smoke-test.js 可以用 node 直接跑，不必起浏览器。
 *
 * 两处清单必须与 Python 侧逐字保持一致，改动前先对齐：
 *   NUMERIC_DIMS  <- scripts/style_profile.py::_NUMERIC_DIMS
 *   BANNED_KEYS   <- tests/test_style_learning.py::test_profile_contains_no_geometry_or_identity_fields
 *
 * 这不是洁癖。风格画像是这个 skill 的身份安全边界：画像里只要出现一个几何字段，
 * 下游就能改脸，而到那时再多的提示词也拦不住。前端只是把同一条边界再守一遍。
 */
(function (root) {
  "use strict";

  var NUMERIC_DIMS = [
    ["exposure", "mean_luma"],
    ["exposure", "median_luma"],
    ["exposure", "contrast"],
    ["exposure", "shadow_lift"],
    ["exposure", "highlight_rolloff"],
    ["white_balance", "r_gain"],
    ["white_balance", "b_gain"],
    ["color", "mean_saturation"],
    ["skin", "target_luma"],
    ["skin", "warmth"],
    ["background", "vignette"],
    ["lighting", "softness"],
    ["lighting", "shadow_depth"],
    ["texture", "grain"],
    ["texture", "microcontrast"],
    ["texture", "halation"]
  ];

  var BANNED_KEYS = [
    "face", "face_shape", "facemesh", "landmark", "landmarks", "eye",
    "eyes", "nose", "mouth", "lips", "jaw", "chin", "pose", "hair",
    "hairstyle", "body", "embedding", "identity", "arcface", "mesh",
    "warp", "thin", "slim", "enlarge", "geometry", "keypoint"
  ];

  var DIM_LABELS = {
    "exposure.mean_luma": "平均亮度",
    "exposure.median_luma": "中位亮度",
    "exposure.contrast": "对比度",
    "exposure.shadow_lift": "暗部抬升",
    "exposure.highlight_rolloff": "高光过渡",
    "white_balance.r_gain": "红通道增益",
    "white_balance.b_gain": "蓝通道增益",
    "color.mean_saturation": "平均饱和度",
    "skin.target_luma": "肤色亮度",
    "skin.warmth": "肤色冷暖",
    "background.vignette": "暗角",
    "lighting.softness": "光线柔和度",
    "lighting.shadow_depth": "阴影深度",
    "texture.grain": "颗粒",
    "texture.microcontrast": "微反差",
    "texture.halation": "高光光晕"
  };

  /* 内置静态风格库。数值是手写示例，不是从真实照片学出来的 —— 真实画像应由
   * scripts/style_profile.py learn 产生。字段结构与它保持一致，将来换成真实
   * 数据时前端不需要改。
   *
   * 注意：这里没有 skin.coverage。那是「某张照片里皮肤占多少」，属于被测照片的
   * 属性，不是风格的属性 —— 混风格时把它平均是没有意义的。
   */
  var MOCK_LIBRARY = [
    {
      id: "cream-white",
      name: "奶油暖白",
      role: "color",
      exposure: { mean_luma: 0.68, median_luma: 0.70, contrast: 0.15, shadow_lift: 0.42, highlight_rolloff: 0.94 },
      white_balance: { r_gain: 0.90, b_gain: 1.12, temperature_hint: "warm" },
      color: { mean_saturation: 0.26, dominant_hues: [30, 40, 200] },
      skin: { tone_hex: "#EBCBAE", target_luma: 0.78, warmth: 14.0 },
      background: { tone_hex: "#E8DFD2", vignette: 0.01 },
      lighting: { direction: "left", softness: 0.74, shadow_depth: 0.16 },
      texture: { grain: 0.008, microcontrast: 0.10, halation: 0.12 },
      mood: ["柔和", "干净", "暖调"]
    },
    {
      id: "korean-clear",
      name: "韩系清透",
      role: "color",
      exposure: { mean_luma: 0.66, median_luma: 0.68, contrast: 0.17, shadow_lift: 0.38, highlight_rolloff: 0.93 },
      white_balance: { r_gain: 1.04, b_gain: 0.98, temperature_hint: "neutral" },
      color: { mean_saturation: 0.22, dominant_hues: [20, 190, 210] },
      skin: { tone_hex: "#F0D9C4", target_luma: 0.80, warmth: 9.0 },
      background: { tone_hex: "#EDEAE4", vignette: 0.01 },
      lighting: { direction: "front", softness: 0.68, shadow_depth: 0.20 },
      texture: { grain: 0.006, microcontrast: 0.22, halation: 0.08 },
      mood: ["清透", "明亮", "低饱和"]
    },
    {
      id: "forest-green",
      name: "森系绿",
      role: "color",
      exposure: { mean_luma: 0.52, median_luma: 0.53, contrast: 0.21, shadow_lift: 0.24, highlight_rolloff: 0.90 },
      white_balance: { r_gain: 1.02, b_gain: 1.06, temperature_hint: "cool" },
      color: { mean_saturation: 0.36, dominant_hues: [90, 120, 40] },
      skin: { tone_hex: "#DFC0A2", target_luma: 0.68, warmth: 8.0 },
      background: { tone_hex: "#8A9A70", vignette: 0.03 },
      lighting: { direction: "top", softness: 0.55, shadow_depth: 0.28 },
      texture: { grain: 0.014, microcontrast: 0.20, halation: 0.16 },
      mood: ["自然", "户外", "草本绿"]
    },
    {
      id: "sunset-camp",
      name: "日落露营",
      role: "color",
      exposure: { mean_luma: 0.48, median_luma: 0.46, contrast: 0.25, shadow_lift: 0.20, highlight_rolloff: 0.88 },
      white_balance: { r_gain: 0.84, b_gain: 1.24, temperature_hint: "warm" },
      color: { mean_saturation: 0.46, dominant_hues: [25, 35, 15] },
      skin: { tone_hex: "#D9A87E", target_luma: 0.64, warmth: 20.0 },
      background: { tone_hex: "#6B4A32", vignette: 0.05 },
      lighting: { direction: "right", softness: 0.42, shadow_depth: 0.34 },
      texture: { grain: 0.032, microcontrast: 0.26, halation: 0.38 },
      mood: ["黄昏", "温暖", "胶片感"]
    },
    {
      id: "french-vintage",
      name: "法式复古",
      role: "color",
      exposure: { mean_luma: 0.58, median_luma: 0.59, contrast: 0.18, shadow_lift: 0.34, highlight_rolloff: 0.91 },
      white_balance: { r_gain: 0.96, b_gain: 1.06, temperature_hint: "warm" },
      color: { mean_saturation: 0.30, dominant_hues: [35, 25, 45] },
      skin: { tone_hex: "#E3C4A8", target_luma: 0.72, warmth: 13.0 },
      background: { tone_hex: "#C4B49C", vignette: 0.04 },
      lighting: { direction: "left", softness: 0.62, shadow_depth: 0.22 },
      texture: { grain: 0.020, microcontrast: 0.14, halation: 0.22 },
      mood: ["复古", "哑光", "低反差"]
    }
  ];

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function round4(value) {
    return Math.round(value * 10000) / 10000;
  }

  /* profile.get(name, {}) 在键存在但值为 null 时会返回 null —— 这是 Python 侧踩过
   * 的坑（见 scripts/build_generation_prompt.py::_section）。画像可能被手工编辑过，
   * 也可能来自别的生成器版本，所以这里同样只接受真正的对象。 */
  function sectionOf(profile, name) {
    var value = profile ? profile[name] : null;
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function walk(node, trail, visit) {
    if (Array.isArray(node)) {
      node.forEach(function (item, index) {
        walk(item, trail + "[" + index + "]", visit);
      });
      return;
    }
    if (node && typeof node === "object") {
      Object.keys(node).forEach(function (key) {
        var next = trail ? trail + "." + key : key;
        visit(key, next);
        walk(node[key], next, visit);
      });
    }
  }

  function assertNoIdentityFields(profile) {
    walk(profile, "", function (key, trail) {
      if (BANNED_KEYS.indexOf(String(key).toLowerCase()) !== -1) {
        throw new Error("风格画像不允许包含身份/几何字段 " + key + "（位置：" + trail + "）");
      }
    });
    return true;
  }

  function parseHex(hex) {
    var text = String(hex || "").trim().replace(/^#/, "");
    if (!/^[0-9a-fA-F]{6}$/.test(text)) {
      return [128, 128, 128];
    }
    return [
      parseInt(text.slice(0, 2), 16),
      parseInt(text.slice(2, 4), 16),
      parseInt(text.slice(4, 6), 16)
    ];
  }

  function toHex(rgb) {
    return "#" + rgb.map(function (channel) {
      var clamped = Math.max(0, Math.min(255, Math.round(channel)));
      return clamped.toString(16).padStart(2, "0");
    }).join("").toUpperCase();
  }

  function blendHex(items) {
    var r = 0, g = 0, b = 0, total = 0;
    items.forEach(function (item) {
      var rgb = parseHex(item.hex);
      r += rgb[0] * item.weight;
      g += rgb[1] * item.weight;
      b += rgb[2] * item.weight;
      total += item.weight;
    });
    if (total > 0) {
      r /= total;
      g /= total;
      b /= total;
    }
    return toHex([r, g, b]);
  }

  /* 权重归一化。全部为 0 或负数时改取均分 —— 用户把三个滑块都拖到 0 是常见操作，
   * 报一个错让他自己想明白，不如直接给他一个合理结果。 */
  function normaliseWeights(entries) {
    var cleaned = entries.map(function (entry) {
      var weight = Number(entry && entry.weight);
      return {
        profile: entry.profile,
        weight: isFinite(weight) && weight > 0 ? weight : 0
      };
    });
    var sum = cleaned.reduce(function (acc, entry) { return acc + entry.weight; }, 0);
    if (sum <= 0) {
      var even = 1 / cleaned.length;
      return cleaned.map(function (entry) { return { profile: entry.profile, weight: even }; });
    }
    return cleaned.map(function (entry) {
      return { profile: entry.profile, weight: entry.weight / sum };
    });
  }

  function mixedName(normalised) {
    return normalised.map(function (entry) {
      return entry.profile.name + " " + Math.round(entry.weight * 100) + "%";
    }).join(" + ");
  }

  /* 混合风格。
   *
   * Python 的 _merge_profiles 对多张参考图取中位数；这里是加权平均 —— 两者解决的是
   * 不同的问题：多张参考图描述同一个风格，中位数能压掉离群的那张；而加权混合是
   * 用户主动要求「七分这个、三分那个」，必须让权重真正生效，中位数做不到。
   *
   * 数值维度按权重加权平均；两个颜色（肤色、背景色）按权重混色；其余字段
   * （mood、dominant_hues、光线方向等）是分类量，取权重最高的那份 —— 把「光线
   * 方向」平均成 0.63 个「左」是没有意义的。 */
  function mixProfiles(entries) {
    if (!entries || !entries.length) {
      throw new Error("mixProfiles: 至少需要选择一个风格");
    }
    var normalised = normaliseWeights(entries);
    normalised.forEach(function (entry) {
      if (!entry.profile) {
        throw new Error("mixProfiles: 存在缺少画像的条目");
      }
      assertNoIdentityFields(entry.profile);
    });

    var dominant = normalised.reduce(function (a, b) {
      return b.weight > a.weight ? b : a;
    });
    var base = dominant.profile;
    var mixed = clone(base);

    NUMERIC_DIMS.forEach(function (dim) {
      var section = dim[0];
      var key = dim[1];
      var fallback = Number(sectionOf(base, section)[key]) || 0;
      var total = 0;
      normalised.forEach(function (entry) {
        var value = Number(sectionOf(entry.profile, section)[key]);
        total += (isFinite(value) ? value : fallback) * entry.weight;
      });
      mixed[section] = mixed[section] || {};
      mixed[section][key] = round4(total);
    });

    ["skin", "background"].forEach(function (section) {
      mixed[section] = mixed[section] || {};
      mixed[section].tone_hex = blendHex(normalised.map(function (entry) {
        return { hex: sectionOf(entry.profile, section).tone_hex, weight: entry.weight };
      }));
    });

    mixed.id = "";
    mixed.name = mixedName(normalised);
    mixed.source = {
      generator: "child-photoShop-skill/style-library",
      role: base.role || "color",
      mixedFrom: normalised.map(function (entry) {
        return {
          id: entry.profile.id,
          name: entry.profile.name,
          weight: round4(entry.weight)
        };
      })
    };
    return mixed;
  }

  function summarise(profile) {
    return NUMERIC_DIMS.map(function (dim) {
      var id = dim[0] + "." + dim[1];
      return {
        id: id,
        label: DIM_LABELS[id] || id,
        value: Number(sectionOf(profile, dim[0])[dim[1]])
      };
    });
  }

  /* ---- 以下三个是「接口」，当前全是占位实现 ---- */

  function loadStyleLibrary() {
    // 占位：真实实现应向后端请求风格库。当前返回内置静态数据。
    var library = clone(MOCK_LIBRARY);
    library.forEach(assertNoIdentityFields);
    return library;
  }

  function saveStyle(profile) {
    // 占位：真实实现应写入后端或本地存储。当前只做校验，不落盘。
    assertNoIdentityFields(profile);
    return { ok: true, persisted: false, note: "占位实现：未接入后端，未落盘" };
  }

  function exportProfile(profile) {
    // 真实可用：把画像序列化成 JSON 文本，交给调用方下载。
    assertNoIdentityFields(profile);
    return JSON.stringify(profile, null, 2);
  }

  var api = {
    NUMERIC_DIMS: NUMERIC_DIMS,
    BANNED_KEYS: BANNED_KEYS,
    DIM_LABELS: DIM_LABELS,
    MOCK_LIBRARY: MOCK_LIBRARY,
    assertNoIdentityFields: assertNoIdentityFields,
    blendHex: blendHex,
    exportProfile: exportProfile,
    loadStyleLibrary: loadStyleLibrary,
    mixProfiles: mixProfiles,
    normaliseWeights: normaliseWeights,
    parseHex: parseHex,
    saveStyle: saveStyle,
    summarise: summarise,
    toHex: toHex
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.StyleLibrary = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
