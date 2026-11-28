/* ============================================================================
 * DirCleaner 内置自检（仅存在于测试版产品文件，正式版没有）
 * ----------------------------------------------------------------------------
 * 由 build_test_version.py 注入到 body 结束标签之前，包在 TEST_SELFTEST_START/END 之间。
 *
 * 注意：本文件会被内联进 HTML 的 script 块，源码里不得出现
 * 「小于号 + 斜杠 + 字母」序列（含 script/body 等标签名），否则 HTML
 * 解析器会提前结束脚本。构造成对标签请一律用 DOM API。
 *
 * 设计约束：
 *   · 黑盒：只操作 DOM 与公开事件；**不触碰文件系统**。
 *     目录选择、清空、白名单写入都需要真实目录句柄，自检一律不触发。
 *   · 无污染：主题（不持久化）与主题菜单开合状态在 finally 里复原。
 *   · 不自动运行；每项独立 try / catch。
 * ========================================================================== */
(function () {
  'use strict';

  var PROBE_KEY = '__dircleaner_selftest_probe__';
  var results = [];

  function pass(name, detail) { results.push({ ok: true, name: name, detail: detail || '' }); }
  function fail(name, detail) { results.push({ ok: false, name: name, detail: detail || '' }); }

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function check(name, fn) {
    try {
      var out = fn();
      if (out && typeof out.then === 'function') {
        return out.then(function (v) {
          if (v === false) fail(name, '返回 false');
          else pass(name, typeof out === 'string' ? out : '');
        }, function (e) {
          fail(name, (e && e.message) ? e.message : String(e));
        });
      }
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
      check('关键节点 id 齐全', function () {
        var ids = ['themeBtn', 'themeMenu', 'dirPath', 'browseBtn', 'lastDirBtn',
                   'confirmCheck', 'confirmNameInput', 'confirmNameRow', 'whitelistList',
                   'startBtn', 'cancelBtn', 'logOutput', 'statusText'];
        var missing = ids.filter(function (id) { return !document.getElementById(id); });
        if (missing.length) throw new Error('缺少：' + missing.join(', '));
        return ids.length + ' 个 id 全部存在';
      }),
      check('启动日志已写入', function () {
        var txt = (document.getElementById('logOutput') || {}).textContent || '';
        if (txt.indexOf('DirCleaner 已就绪') < 0) throw new Error('未看到就绪日志：' + txt.slice(0, 40));
        return '就绪日志存在';
      }),
      check('统计卡片已初始化', function () {
        var ids = ['totalFiles', 'totalDirs', 'totalSize', 'totalErrors'];
        var bad = ids.filter(function (id) {
          var n = document.getElementById(id);
          return !n || !String(n.textContent || '').trim();
        });
        if (bad.length) throw new Error('未初始化：' + bad.join(', '));
        return ids.length + ' 项已初始化';
      }),
      check('许可证声明存在', function () {
        var html = document.documentElement.innerHTML || '';
        if (html.indexOf('本程序是自由软件') < 0) throw new Error('未找到 GPLv3 声明');
        return 'GPLv3 声明存在';
      })
    ]);
  }

  /* ---------------- 样式 ---------------- */

  function styleChecks() {
    return Promise.all([
      check('主题令牌可解析', function () {
        var names = ['--md-sys-color-primary', '--md-sys-color-surface', '--md-sys-color-on-surface'];
        var empty = names.filter(function (n) {
          return !getComputedStyle(document.body).getPropertyValue(n).trim();
        });
        if (empty.length) throw new Error('空值：' + empty.join(', '));
        return names.length + ' 个令牌均有值';
      }),
      check('body 带主题类名', function () {
        var cls = document.body.className || '';
        if (!/\btheme-\d+\b/.test(cls)) throw new Error('body 类名为 ' + JSON.stringify(cls));
        return cls.match(/\btheme-\d+\b/)[0];
      }),
      check('主题选项共 8 个', function () {
        var opts = $$('#themeMenu .theme-option');
        if (opts.length !== 8) throw new Error('实际 ' + opts.length + ' 个');
        var active = opts.filter(function (o) {
          return o.getAttribute('aria-pressed') === 'true';
        });
        if (active.length !== 1) throw new Error('aria-pressed=true 的有 ' + active.length + ' 个');
        return '8 个选项，1 个选中';
      })
    ]);
  }

  /* ---------------- 交互 ---------------- */

  function interactionChecks() {
    var errCount = 0;
    function onErr() { errCount++; }
    window.addEventListener('error', onErr);
    window.addEventListener('unhandledrejection', onErr);

    var themeBefore = (function () {
      var opts = $$('#themeMenu .theme-option');
      var on = opts.filter(function (o) { return o.getAttribute('aria-pressed') === 'true'; })[0];
      return on ? on.getAttribute('data-theme') : '0';
    })();
    // 只记录「快照时是否已有内容」。updateWhitelistUI 是异步的，启动日志
    // 可能晚于快照才写入；若把空串当快照无条件回写，restore 反而会擦掉
    // 刚出现的就绪日志。所以快照为空时不动它。
    var logNode = document.getElementById('logOutput');
    var logBefore = logNode ? logNode.innerHTML : '';

    function restore() {
      var menu = document.getElementById('themeMenu');
      if (menu) menu.style.display = 'none';
      var btn = document.getElementById('themeBtn');
      if (btn) btn.setAttribute('aria-expanded', 'false');
      var opt = $$('#themeMenu .theme-option').filter(function (o) {
        return o.getAttribute('data-theme') === themeBefore;
      })[0];
      if (opt) opt.click();
      // 自检清过一次日志，这里原样放回；快照为空说明当时还没日志，
      // 后续写入的日志属于产品自己，不能覆盖
      var log = document.getElementById('logOutput');
      if (log && logBefore) log.innerHTML = logBefore;
      // 确认框回到未勾选、名称框回到禁用（防止自检中途留下半勾状态）
      var chk = document.getElementById('confirmCheck');
      if (chk && chk.checked) {
        chk.checked = false;
        chk.dispatchEvent(new Event('change', { bubbles: true }));
      }
      window.removeEventListener('error', onErr);
      window.removeEventListener('unhandledrejection', onErr);
    }

    return (async function () {
      try {
        await check('主题菜单开合 + aria 同步', function () {
          var btn = document.getElementById('themeBtn');
          var menu = document.getElementById('themeMenu');
          var before = getComputedStyle(menu).display !== 'none';
          btn.click();
          var open = getComputedStyle(menu).display !== 'none';
          if (before === open) throw new Error('可见性未变化（' + before + '）');
          if (btn.getAttribute('aria-expanded') !== 'true') throw new Error('aria-expanded 未置 true');
          btn.click();
          if (getComputedStyle(menu).display !== 'none') throw new Error('再次点击未收起');
          if (btn.getAttribute('aria-expanded') !== 'false') throw new Error('aria-expanded 未复位');
          return '开 → 关正常';
        });

        await check('切换主题后 body 类名变化', function () {
          var opts = $$('#themeMenu .theme-option');
          var current = themeBefore;
          var target = opts.filter(function (o) {
            return o.getAttribute('data-theme') !== current;
          })[0];
          if (!target) throw new Error('找不到其它主题');
          var beforeCls = document.body.className;
          target.click();
          var afterCls = document.body.className;
          if (beforeCls === afterCls) throw new Error('body 类名未变化：' + afterCls);
          if (target.getAttribute('aria-pressed') !== 'true') throw new Error('aria-pressed 未同步');
          return current + ' → ' + target.getAttribute('data-theme');
        });

        await check('确认复选框驱动名称输入框', function () {
          // 初始态由 updateWhitelistUI 决定（未选目录时会主动放开输入框），
          // 因此不断言初始 disabled，只断言勾选 / 取消这一对驱动关系。
          var chk = document.getElementById('confirmCheck');
          var inp = document.getElementById('confirmNameInput');
          chk.checked = true;
          chk.dispatchEvent(new Event('change', { bubbles: true }));
          if (inp.disabled !== false) throw new Error('勾选后输入框应可输入');
          chk.checked = false;
          chk.dispatchEvent(new Event('change', { bubbles: true }));
          if (inp.disabled !== true) throw new Error('取消勾选后应回到禁用');
          if (inp.value !== '') throw new Error('取消勾选后输入内容应清空');
          return '禁用 → 可输入 → 禁用';
        });

        await check('未选目录时开始按钮禁用', function () {
          var btn = document.getElementById('startBtn');
          if (!btn.disabled) throw new Error('startBtn 未禁用');
          return 'disabled';
        });

        await check('清空日志按钮可用', function () {
          var log = document.getElementById('logOutput');
          if (!log.textContent.trim()) throw new Error('日志本来就是空的');
          document.getElementById('clearLogBtn').click();
          if (log.textContent.trim()) throw new Error('点击后日志未清空');
          return '已清空';
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
      'justify-content:center;background:rgba(0,0,0,.55);padding:20px}' +
      '#selftestModal .st-box{width:100%;max-width:680px;max-height:86vh;overflow:auto;' +
      'background:var(--md-sys-color-surface,#fff);color:var(--md-sys-color-on-surface,#111827);' +
      'border:1px solid var(--md-sys-color-outline,#6b7280);border-radius:12px;' +
      'padding:18px 20px;box-shadow:0 18px 60px rgba(0,0,0,.35)}' +
      '#selftestModal h2{margin:0 0 10px;font-size:1.05rem}' +
      '#selftestModal ul{list-style:none;margin:0;padding:0;font-size:.85rem}' +
      '#selftestModal li{display:flex;gap:8px;align-items:flex-start;padding:3px 0}' +
      '#selftestModal .st-tag{flex:0 0 42px;font-family:monospace}' +
      '#selftestModal .st-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}' +
      '#selftestModal button{cursor:pointer;padding:6px 12px;border-radius:8px;' +
      'border:1px solid var(--md-sys-color-outline,#6b7280);' +
      'background:var(--md-sys-color-surface-variant,#f8fafc);' +
      'color:var(--md-sys-color-on-surface,#111827);font-size:.85rem}' +
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
    note.style.cssText = 'margin:14px 0 0;color:var(--md-sys-color-on-surface-variant,#4b5563);' +
      'font-size:.78rem';
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

  // 产品在 window.load 里初始化（主题、白名单、日志）。点得早会看到
  // 空日志，因此等到「已就绪」那行出现再跑。
  function waitReady(timeoutMs) {
    var started = Date.now();
    function ready() {
      var log = document.getElementById('logOutput');
      return !!(log && log.textContent.indexOf('DirCleaner 已就绪') >= 0);
    }
    return new Promise(function (resolve) {
      (function tick() {
        if (ready() || Date.now() - started > timeoutMs) return resolve();
        setTimeout(tick, 100);
      })();
    });
  }

  async function run() {
    results = [];
    injectStyle();
    await waitReady(15000);
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
    var h1 = document.querySelector('.app-header h1');
    if (h1 && !document.getElementById('testBadge')) {
      var badge = document.createElement('span');
      badge.id = 'testBadge';
      badge.textContent = 'TEST';
      h1.appendChild(badge);
    }
    var anchor = document.getElementById('themeBtn');
    if (anchor && !document.getElementById('selftestBtn')) {
      var btn = document.createElement('button');
      btn.id = 'selftestBtn';
      btn.className = 'theme-btn';
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
