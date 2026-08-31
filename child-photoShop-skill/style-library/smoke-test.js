/* 冒烟测试：node smoke-test.js
 *
 * 零依赖，只用 node 内置模块。目的是在不开浏览器的前提下证明纯逻辑层没坏 ——
 * 界面出问题肉眼能看见，混合系数算错了肉眼看不见。
 *
 * 用法：node smoke-test.js
 * 退出码 0 表示全部通过，1 表示有失败。
 */
"use strict";

var assert = require("assert");
var lib = require("./profile-library.js");

var passed = 0;
var failed = 0;

function check(name, fn) {
  try {
    fn();
    passed += 1;
    console.log("  ok   " + name);
  } catch (error) {
    failed += 1;
    console.log("  FAIL " + name);
    console.log("       " + error.message);
  }
}

function byId(library, id) {
  var found = library.filter(function (profile) { return profile.id === id; });
  assert.strictEqual(found.length, 1, "风格库中应恰好有一份 " + id);
  return found[0];
}

console.log("风格画像库冒烟测试");
console.log("");

console.log("[数据]");
check("内置风格库能加载且非空", function () {
  var library = lib.loadStyleLibrary();
  assert.ok(library.length >= 5, "风格数量应不少于 5，实际 " + library.length);
});

check("每份画像都有 id 与 name", function () {
  lib.loadStyleLibrary().forEach(function (profile) {
    assert.ok(profile.id, "缺少 id");
    assert.ok(profile.name, "缺少 name");
  });
});

check("内置画像全部不含身份/几何字段", function () {
  lib.loadStyleLibrary().forEach(function (profile) {
    lib.assertNoIdentityFields(profile);
  });
});

check("数值维度清单与画像字段对得上", function () {
  lib.loadStyleLibrary().forEach(function (profile) {
    lib.NUMERIC_DIMS.forEach(function (dim) {
      var value = profile[dim[0]] && profile[dim[0]][dim[1]];
      assert.strictEqual(typeof value, "number", profile.id + " 缺少 " + dim.join("."));
    });
  });
});

console.log("");
console.log("[身份安全]");
check("含 face 字段的画像会被拒绝", function () {
  assert.throws(function () {
    lib.assertNoIdentityFields({ exposure: { mean_luma: 0.5 }, face: { width: 100 } });
  }, /face/);
});

check("嵌套在深处的几何字段也会被揪出来", function () {
  assert.throws(function () {
    lib.assertNoIdentityFields({ skin: { tone_hex: "#FFFFFF", landmark: [0, 1] } });
  }, /landmark/);
});

check("导出含身份字段的画像会抛错而不是静默放行", function () {
  assert.throws(function () {
    lib.exportProfile({ name: "坏画像", jaw: 0.8 });
  }, /jaw/);
});

console.log("");
console.log("[权重归一化]");
check("权重按比例归一化", function () {
  var out = lib.normaliseWeights([{ weight: 1 }, { weight: 3 }]);
  assert.strictEqual(out[0].weight, 0.25);
  assert.strictEqual(out[1].weight, 0.75);
});

check("权重全为 0 时改为均分而不是报错", function () {
  var out = lib.normaliseWeights([{ weight: 0 }, { weight: 0 }, { weight: 0 }]);
  out.forEach(function (entry) {
    assert.ok(Math.abs(entry.weight - 1 / 3) < 1e-9, "应为 1/3，实际 " + entry.weight);
  });
});

check("负权重被当作 0 处理", function () {
  var out = lib.normaliseWeights([{ weight: -5 }, { weight: 5 }]);
  assert.strictEqual(out[0].weight, 0);
  assert.strictEqual(out[1].weight, 1);
});

console.log("");
console.log("[混合]");
check("五五开等于两个风格的中点", function () {
  var library = lib.loadStyleLibrary();
  var a = byId(library, "cream-white");
  var b = byId(library, "sunset-camp");
  var mixed = lib.mixProfiles([
    { profile: a, weight: 50 },
    { profile: b, weight: 50 }
  ]);
  var expected = (a.exposure.mean_luma + b.exposure.mean_luma) / 2;
  assert.ok(
    Math.abs(mixed.exposure.mean_luma - expected) < 1e-4,
    "平均亮度应为 " + expected + "，实际 " + mixed.exposure.mean_luma
  );
});

check("七三开的权重真的生效（不是取中位数）", function () {
  var library = lib.loadStyleLibrary();
  var a = byId(library, "cream-white");
  var b = byId(library, "sunset-camp");
  var mixed = lib.mixProfiles([
    { profile: a, weight: 70 },
    { profile: b, weight: 30 }
  ]);
  var expected = a.exposure.mean_luma * 0.7 + b.exposure.mean_luma * 0.3;
  assert.ok(
    Math.abs(mixed.exposure.mean_luma - expected) < 1e-4,
    "平均亮度应为 " + expected + "，实际 " + mixed.exposure.mean_luma
  );
});

check("只选一个风格时结果与该风格一致", function () {
  var library = lib.loadStyleLibrary();
  var a = byId(library, "forest-green");
  var mixed = lib.mixProfiles([{ profile: a, weight: 1 }]);
  lib.NUMERIC_DIMS.forEach(function (dim) {
    assert.strictEqual(mixed[dim[0]][dim[1]], a[dim[0]][dim[1]], "维度 " + dim.join(".") + " 被改动了");
  });
});

check("空输入会抛错而不是返回空对象", function () {
  assert.throws(function () { lib.mixProfiles([]); }, /至少/);
});

check("混合结果带得清来源与配比", function () {
  var library = lib.loadStyleLibrary();
  var mixed = lib.mixProfiles([
    { profile: byId(library, "cream-white"), weight: 70 },
    { profile: byId(library, "korean-clear"), weight: 30 }
  ]);
  assert.strictEqual(mixed.source.mixedFrom.length, 2);
  assert.strictEqual(mixed.source.mixedFrom[0].weight, 0.7);
  assert.ok(mixed.name.indexOf("70%") !== -1, "名称里应带配比，实际 " + mixed.name);
});

check("分类字段跟权重最高的那份，不做平均", function () {
  var library = lib.loadStyleLibrary();
  var warm = byId(library, "sunset-camp");
  var mixed = lib.mixProfiles([
    { profile: warm, weight: 80 },
    { profile: byId(library, "korean-clear"), weight: 20 }
  ]);
  assert.strictEqual(mixed.lighting.direction, warm.lighting.direction);
});

check("混合结果仍然不含身份字段", function () {
  var library = lib.loadStyleLibrary();
  var mixed = lib.mixProfiles([
    { profile: byId(library, "cream-white"), weight: 1 },
    { profile: byId(library, "forest-green"), weight: 1 }
  ]);
  lib.assertNoIdentityFields(mixed);
});

console.log("");
console.log("[颜色与导出]");
check("颜色按权重混色", function () {
  var result = lib.blendHex([
    { hex: "#000000", weight: 0.5 },
    { hex: "#FFFFFF", weight: 0.5 }
  ]);
  assert.strictEqual(result, "#808080");
});

check("非法颜色值退化为中性灰而不是崩溃", function () {
  assert.strictEqual(lib.parseHex("nonsense").join(","), "128,128,128");
  assert.strictEqual(lib.parseHex(undefined).join(","), "128,128,128");
});

check("导出的是可解析的 JSON", function () {
  var library = lib.loadStyleLibrary();
  var mixed = lib.mixProfiles([
    { profile: byId(library, "cream-white"), weight: 60 },
    { profile: byId(library, "sunset-camp"), weight: 40 }
  ]);
  var parsed = JSON.parse(lib.exportProfile(mixed));
  assert.strictEqual(parsed.name, mixed.name);
  assert.ok(parsed.source.mixedFrom.length === 2);
});

check("保存接口是占位实现，明确报告未落盘", function () {
  var library = lib.loadStyleLibrary();
  var result = lib.saveStyle(byId(library, "cream-white"));
  assert.strictEqual(result.ok, true);
  assert.strictEqual(result.persisted, false, "占位实现不应声称已落盘");
});

console.log("");
console.log("[摘要]");
check("摘要覆盖全部数值维度且带中文标签", function () {
  var library = lib.loadStyleLibrary();
  var rows = lib.summarise(byId(library, "cream-white"));
  assert.strictEqual(rows.length, lib.NUMERIC_DIMS.length);
  rows.forEach(function (row) {
    assert.ok(row.label, "维度 " + row.id + " 缺少标签");
    assert.strictEqual(typeof row.value, "number");
  });
});

console.log("");
console.log("通过 " + passed + " 项，失败 " + failed + " 项");
process.exit(failed === 0 ? 0 : 1);
