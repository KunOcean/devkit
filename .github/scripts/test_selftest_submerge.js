/* ============================================================================
 * SubMerge Pro 内置自检（仅存在于测试版产品文件，正式版没有）
 * ----------------------------------------------------------------------------
 * 由 build_test_version.py 注入到 body 结束标签之前，包在 TEST_SELFTEST_START/END 之间。
 *
 * 注意：本文件会被内联进 HTML 的 script 块，源码里不得出现
 * 「小于号 + 斜杠 + 字母」序列（含 script/body 等标签名），否则 HTML
 * 解析器会提前结束脚本。构造成对标签请一律用 DOM API。
 *
 * 设计约束：
 *   · 黑盒：只操作 DOM 与公开事件；**不使用剪贴板、不触发下载**。
 *     字幕上传需要真实文件对象，自检不伪造 File，只验证空态与控件联动。
 *   · 无污染：导出模式、目标语言、FPS 下拉在 finally 里复原。
 *   · 不自动运行；每项独立 try / catch。
 * ========================================================================== */
(function () {
  'use strict';

  var PROBE_KEY = '__submerge_selftest_probe__';
  var results = [];

  function pass(name, detail) { results.push({ ok: true, name: name, detail: detail || '' }); }
  function fail(name, detail) { results.push({ ok: false, name: name, detail: detail || '' }); }

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }
  function cssVar(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }

  function check(name, fn) {
    try {
      var out = fn();
      if (out === false) fail(name, '返回 false');
      else pass(name, typeof out === 'string' ? out : '');
    } catch (e) {
      fail(name, (e && e.message) ? e.message : String(e));
    }
    return Promise.resolve();
  }

  /* ---------------- 结构 ---------------- */

  function structureChecks() {
    return Promise.all([
      check('doctype / lang / charset / viewport', function () {
        var html = document.documentElement;
        if (!document.doctype) throw new Error('缺少 doctype');
        if (!html.getAttribute('lang')) throw new Error('html 缺少 lang');
        if (!$('meta[charset]')) throw new Error('缺少 meta charset');
        if (!$('meta[name="viewport"]')) throw new Error('缺少 viewport');
        return html.getAttribute('lang');
      }),
      check('CSP meta 存在且声明 script-src', function () {
        var m = $('meta[http-equiv="Content-Security-Policy"]');
        if (!m) throw new Error('缺少 CSP');
        if ((m.getAttribute('content') || '').indexOf('script-src') < 0) {
          throw new Error('CSP 未声明 script-src');
        }
        return 'OK';
      }),
      check('关键节点 id 齐全', function () {
        var ids = ['dropZone', 'fileInput', 'langNameInput', 'presetLangSelect',
                   'fpsRow', 'fpsSelect', 'translationInput', 'mergedTextView',
                   'mergeBtn', 'undoBtn', 'exportBtn', 'resetBtn', 'tableBody',
                   'exportModeGroup', 'entryCountDisplay'];
        var missing = ids.filter(function (id) { return !document.getElementById(id); });
        if (missing.length) throw new Error('缺少：' + missing.join(', '));
        return ids.length + ' 个 id 全部存在';
      }),
      check('初始为空态', function () {
        var txt = document.getElementById('entryCountDisplay').textContent || '';
        if (txt.indexOf('未加载字幕') < 0) throw new Error('状态栏为：' + txt);
        var rows = document.querySelectorAll('#tableBody tr');
        if (rows.length !== 1) throw new Error('预览表行数 ' + rows.length);
        return '未加载字幕 + 空提示行';
      }),
      check('许可证声明存在', function () {
        var txt = document.body.textContent || '';
        if (txt.indexOf('本程序是自由软件') < 0) throw new Error('未找到 GPLv3 声明');
        return 'GPLv3 声明存在';
      })
    ]);
  }

  /* ---------------- 样式 ---------------- */

  function styleChecks() {
    return Promise.all([
      check('CSS 变量可解析', function () {
        var names = ['--bg', '--text', '--accent'];
        var empty = names.filter(function (n) { return !cssVar(n); });
        if (empty.length) throw new Error('空值：' + empty.join(', '));
        return names.join(' / ') + ' 均有值';
      }),
      check('body 带皮肤类名', function () {
        var cls = document.body.className || '';
        if (!/\bskin-\w+\b/.test(cls)) throw new Error('body 类名为 ' + JSON.stringify(cls));
        return cls.match(/\bskin-\w+\b/)[0];
      }),
      check('空态下操作按钮禁用', function () {
        var ids = ['mergeBtn', 'undoBtn', 'exportBtn', 'resetBtn', 'copyMergedBtn'];
        var enabled = ids.filter(function (id) {
          var n = document.getElementById(id);
          return n && !n.disabled;
        });
        if (enabled.length) throw new Error('未禁用：' + enabled.join(', '));
        return '5 个按钮均为禁用';
      })
    ]);
  }

  /* ---------------- 交互 ---------------- */

  function interactionChecks() {
    var errCount = 0;
    function onErr() { errCount++; }
    window.addEventListener('error', onErr);
    window.addEventListener('unhandledrejection', onErr);

    var langBefore = (document.getElementById('langNameInput') || {}).value || '';
    var presetBefore = (document.getElementById('presetLangSelect') || {}).value || '';
    var fpsBefore = (document.getElementById('fpsSelect') || {}).value || '25';
    var fpsCustomBefore = (document.getElementById('fpsCustomInput') || {}).value || '25';
    var translationBefore = (document.getElementById('translationInput') || {}).value || '';
    var modeBefore = (function () {
      var on = $('#exportModeGroup .mode-btn.active');
      return on ? on.getAttribute('data-mode') : 'both';
    })();

    function restore() {
      var modeBtn = $$('#exportModeGroup .mode-btn').filter(function (b) {
        return b.getAttribute('data-mode') === modeBefore;
      })[0];
      if (modeBtn) modeBtn.click();
      var lang = document.getElementById('langNameInput');
      if (lang) lang.value = langBefore;
      var preset = document.getElementById('presetLangSelect');
      if (preset) preset.value = presetBefore;
      var fps = document.getElementById('fpsSelect');
      if (fps) {
        fps.value = fpsBefore;
        fps.dispatchEvent(new Event('change', { bubbles: true }));
      }
      var custom = document.getElementById('fpsCustomInput');
      if (custom) custom.value = fpsCustomBefore;
      var ta = document.getElementById('translationInput');
      if (ta) ta.value = translationBefore;
      window.removeEventListener('error', onErr);
      window.removeEventListener('unhandledrejection', onErr);
    }

    return (async function () {
      try {
        await check('预设语言下拉已填充且可联动', function () {
          var sel = document.getElementById('presetLangSelect');
          if (sel.options.length < 10) throw new Error('只有 ' + sel.options.length + ' 项');
          var target = Array.prototype.slice.call(sel.options).filter(function (o) {
            return o.value !== sel.value;
          })[0];
          if (!target) throw new Error('找不到其它语言');
          sel.value = target.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          var input = document.getElementById('langNameInput');
          if (input.value !== target.value) {
            throw new Error('目标语言未联动：' + input.value + ' vs ' + target.value);
          }
          return sel.options.length + ' 个预设 · 联动为 ' + target.value;
        });

        await check('FPS 选择「自定义」显示输入框', function () {
          var sel = document.getElementById('fpsSelect');
          var custom = document.getElementById('fpsCustomInput');
          var row = document.getElementById('fpsRow');
          sel.value = 'custom';
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          if (getComputedStyle(custom).display === 'none') {
            throw new Error('自定义输入框未显示');
          }
          sel.value = '25';
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          if (getComputedStyle(custom).display !== 'none') {
            throw new Error('切回固定帧率后输入框未隐藏');
          }
          if (row.style.display === '') {
            // .srt 空态下整行本应隐藏，切 fps 不应把它打开
            throw new Error('FPS 行不应在非 bcc 空态下显示');
          }
          return '显示 / 隐藏正常';
        });

        await check('导出模式切换', function () {
          var group = document.getElementById('exportModeGroup');
          var btns = $$('#exportModeGroup .mode-btn');
          if (btns.length !== 3) throw new Error('模式按钮 ' + btns.length + ' 个');
          var target = btns.filter(function (b) {
            return !b.classList.contains('active');
          })[0];
          target.click();
          if (!target.classList.contains('active')) throw new Error('点击后未激活');
          var actives = btns.filter(function (b) { return b.classList.contains('active'); });
          if (actives.length !== 1) throw new Error('active 数量 ' + actives.length);
          return modeBefore + ' → ' + target.getAttribute('data-mode');
        });

        await check('粘贴框输入不改变空态', function () {
          var ta = document.getElementById('translationInput');
          ta.value = '[1] 测试译文';
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          var txt = document.getElementById('entryCountDisplay').textContent || '';
          if (txt.indexOf('未加载字幕') < 0) throw new Error('状态栏被改写：' + txt);
          ta.value = '';
          return 'OK';
        });

        await check('localStorage 读写', function () {
          localStorage.setItem(PROBE_KEY, 'ok');
          var v = localStorage.getItem(PROBE_KEY);
          localStorage.removeItem(PROBE_KEY);
          if (v !== 'ok') throw new Error('回读不一致：' + v);
          if (localStorage.getItem(PROBE_KEY) !== null) throw new Error('探针键未清除');
          return '写 / 读 / 删 正常';
        });

        await check('运行期无未捕获异常', function () {
          if (errCount > 0) throw new Error('捕获到 ' + errCount + ' 个异常');
          return '0 个';
        });
      } finally {
        restore();
      }
    })();
  }

  /* ---------------- 结果 UI ---------------- */

  function injectStyle() {
    if (document.getElementById('selftestStyle')) return;
    var st = document.createElement('style');
    st.id = 'selftestStyle';
    st.textContent =
      '#selftestModal{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;' +
      'justify-content:center;background:rgba(0,0,0,.5);padding:20px}' +
      '#selftestModal .st-box{width:100%;max-width:680px;max-height:86vh;overflow:auto;' +
      'background:var(--surface,#fff);color:var(--text,#0f172a);border:1px solid var(--border,#cbd5e1);' +
      'border-radius:12px;padding:18px 20px;box-shadow:0 18px 60px rgba(0,0,0,.35)}' +
      '#selftestModal h2{margin:0 0 10px;font-size:1.05rem}' +
      '#selftestModal ul{list-style:none;margin:0;padding:0;font-size:.85rem}' +
      '#selftestModal li{display:flex;gap:8px;align-items:flex-start;padding:3px 0}' +
      '#selftestModal .st-tag{flex:0 0 42px;font-family:monospace}' +
      '#selftestModal .st-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}' +
      '#selftestModal button{cursor:pointer;padding:6px 12px;border-radius:8px;' +
      'border:1px solid var(--border,#cbd5e1);background:var(--surface-2,#fafcff);color:inherit}' +
      '#testBadge{margin-left:8px;padding:1px 7px;border-radius:999px;background:#ff8a3d;' +
      'color:#08090d;font-size:.66rem;font-weight:700;font-family:ui-monospace,monospace;' +
      'letter-spacing:.06em;vertical-align:middle}';
    document.head.appendChild(st);
  }

  function render() {
    var old = document.getElementById('selftestModal');
    if (old) old.remove();

    var total = results.length;
    var bad = results.filter(function (r) { return !r.ok; }).length;
    var good = total - bad;

    var wrap = document.createElement('div');
    wrap.id = 'selftestModal';
    wrap.setAttribute('role', 'dialog');
    wrap.setAttribute('aria-modal', 'true');
    wrap.setAttribute('aria-label', '内置自检结果');

    var box = document.createElement('div');
    box.className = 'st-box';

    var h = document.createElement('h2');
    h.textContent = '内置自检';
    box.appendChild(h);

    var summary = document.createElement('p');
    summary.style.cssText = 'margin:0 0 12px;font-weight:600;color:' +
      (bad === 0 ? '#166534' : '#b91c1c');
    summary.textContent = (bad === 0 ? '全部通过：' : '有失败项：') + good + ' / ' + total + ' 通过';
    box.appendChild(summary);

    var ul = document.createElement('ul');
    results.forEach(function (r) {
      var li = document.createElement('li');
      var tag = document.createElement('span');
      tag.className = 'st-tag';
      tag.style.color = r.ok ? '#166534' : '#b91c1c';
      tag.textContent = r.ok ? 'PASS' : 'FAIL';
      var txt = document.createElement('span');
      txt.style.flex = '1';
      txt.textContent = r.name + (r.detail ? ' — ' + r.detail : '');
      li.appendChild(tag);
      li.appendChild(txt);
      ul.appendChild(li);
    });
    box.appendChild(ul);

    var note = document.createElement('p');
    note.style.cssText = 'margin:14px 0 0;color:var(--text2,#475569);font-size:.78rem';
    note.textContent = '这是测试版专属的自检，不改动任何用户数据；开跑前的界面状态已自动恢复。';
    box.appendChild(note);

    var actions = document.createElement('div');
    actions.className = 'st-actions';
    var rerun = document.createElement('button');
    rerun.type = 'button';
    rerun.textContent = '重新运行';
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = '关闭';
    actions.appendChild(rerun);
    actions.appendChild(close);
    box.appendChild(actions);
    wrap.appendChild(box);
    document.body.appendChild(wrap);

    function shut() { wrap.remove(); }
    close.addEventListener('click', shut);
    rerun.addEventListener('click', function () { shut(); setTimeout(run, 0); });
    wrap.addEventListener('click', function (e) { if (e.target === wrap) shut(); });
    document.addEventListener('keydown', function esc(e) {
      if (e.key === 'Escape') { shut(); document.removeEventListener('keydown', esc); }
    });

    return { total: total, bad: bad, good: good };
  }

  async function run() {
    results = [];
    injectStyle();
    await structureChecks();
    await styleChecks();
    await interactionChecks();
    var r = render();
    document.title = (r.bad === 0 ? 'SELFTEST-PASS ' : 'SELFTEST-FAIL ') +
      r.good + '/' + r.total;
  }

  /* ---------------- 注入入口 ---------------- */

  function mount() {
    injectStyle();
    var h1 = document.querySelector('.header-row h1');
    if (h1 && !document.getElementById('testBadge')) {
      var badge = document.createElement('span');
      badge.id = 'testBadge';
      badge.textContent = 'TEST';
      h1.appendChild(badge);
    }
    var anchor = document.getElementById('exportBtn');
    if (anchor && !document.getElementById('selftestBtn')) {
      var btn = document.createElement('button');
      btn.id = 'selftestBtn';
      btn.className = 'btn btn-outline-blue';
      btn.type = 'button';
      btn.textContent = '自检';
      btn.style.color = '#ff8a3d';
      btn.addEventListener('click', function (e) { e.stopPropagation(); run(); });
      anchor.parentNode.insertBefore(btn, anchor);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }

  window.__selftest = run;
})();
