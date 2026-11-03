/* Fixed in-content AdSense units for aspirantdaily.com.
 *
 * Auto ads are switched off in AdSense; this file decides where ads go so they
 * never crowd the content:
 *   - never above the first section of a page (no ad under the title)
 *   - only at a gap before a new section, heading or MCQ card; never inside
 *     worked examples, tables, lists, answer options or card grids
 *   - at least MIN_GAP pixels of content between two ads, and one ad per
 *     PX_PER_AD of content, up to MAX_ADS
 *   - nothing on interactive quiz pages or very short pages
 * Every unit is labelled "Advertisement". To change density, edit the numbers
 * below; to use a different ad unit, change SLOT.
 */
(function () {
  "use strict";
  var CLIENT = "ca-pub-7495143337429327";
  var SLOT = "3676277973";       // responsive display unit
  var MAX_ADS = 6;
  var PX_PER_AD = 2000;          // one ad per this much content height
  var MIN_BEFORE_FIRST = 600;    // px of content before the first ad
  var MIN_GAP = 1500;            // px of content between ads
  var MIN_AFTER_LAST = 500;      // px of content after the last ad
  var NO_AD_PATHS = /^\/(quiz|quiz-selector|result|admin|404)(\.html)?$/;
  var BREAK_TAGS = /^(SECTION|ARTICLE|H2|H3)$/;
  var BREAK_CLASSES = /(^|\s)(mcq-card|mcq-item|content-box)(\s|$)/;
  // Never place an ad inside these.
  var NO_DESCEND = "table,ul,ol,dl,form,nav,details,pre,figure," +
    ".case-study,.highlight-box,.mcq-card,.mcq-item,.mcq-options,.options,.faq-item";

  if (location.hostname !== "www.aspirantdaily.com") return;
  if (NO_AD_PATHS.test(location.pathname)) return;

  function addStyle() {
    var s = document.createElement("style");
    s.textContent =
      ".ad-slot{margin:40px auto;max-width:100%;text-align:center;clear:both}" +
      ".ad-slot .ad-label{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;" +
      "color:#8a8f98;margin-bottom:6px}" +
      ".ad-slot ins{display:block;min-height:100px}";
    document.head.appendChild(s);
  }

  function makeSlot() {
    var wrap = document.createElement("div");
    wrap.className = "ad-slot";
    wrap.setAttribute("role", "complementary");
    wrap.setAttribute("aria-label", "Advertisement");
    var label = document.createElement("span");
    label.className = "ad-label";
    label.textContent = "Advertisement";
    var ins = document.createElement("ins");
    ins.className = "adsbygoogle";
    ins.setAttribute("data-ad-client", CLIENT);
    ins.setAttribute("data-ad-slot", SLOT);
    ins.setAttribute("data-ad-format", "auto");
    ins.setAttribute("data-full-width-responsive", "true");
    wrap.appendChild(label);
    wrap.appendChild(ins);
    return wrap;
  }

  // The element whose children are the page's blocks: <main>, or the single
  // wrapper inside it when <main> only holds one child.
  function contentRoot() {
    var root = document.querySelector("main");
    for (var depth = 0; root && root.children.length === 1 && depth < 3; depth++) {
      root = root.children[0];
    }
    return root;
  }

  // Grids and row flex containers lay children side by side; an ad there
  // would become a card, so never insert into them.
  function stacksVertically(el) {
    var cs = window.getComputedStyle(el);
    if (cs.display.indexOf("grid") !== -1) return false;
    if (cs.display.indexOf("flex") !== -1 && cs.flexDirection.indexOf("column") === -1) return false;
    return true;
  }

  function isBreak(el) {
    return BREAK_TAGS.test(el.tagName) || BREAK_CLASSES.test(el.className || "");
  }

  // Elements an ad may be inserted before, in document order. Tall blocks
  // are searched one or two levels down so long pages get spaced ads too.
  function candidates(parent, depth, out) {
    if (!stacksVertically(parent)) return out;
    var kids = parent.children;
    for (var i = 0; i < kids.length; i++) {
      var el = kids[i];
      if (!el.offsetHeight) continue;
      if (i > 0 && isBreak(el)) out.push(el);
      if (depth < 2 && el.offsetHeight > MIN_GAP && !el.matches(NO_DESCEND)) {
        candidates(el, depth + 1, out);
      }
    }
    return out;
  }

  function place() {
    var root = contentRoot();
    if (!root || document.querySelector(".ad-slot")) return;
    var top = root.getBoundingClientRect().top + window.pageYOffset;
    var height = root.offsetHeight;
    var limit = Math.min(MAX_ADS, Math.round(height / PX_PER_AD));
    if (limit < 1) return;
    // Spread the ads over the whole page rather than bunching them at the top.
    var gap = Math.max(MIN_GAP, height / (limit + 1));

    // Measure every candidate first, then insert, so earlier ads do not
    // shift the measurements.
    var spots = candidates(root, 0, []).map(function (el) {
      return { el: el, y: el.getBoundingClientRect().top + window.pageYOffset - top };
    }).sort(function (a, b) { return a.y - b.y; });

    var chosen = [];
    var last = -Infinity;
    for (var i = 0; i < spots.length && chosen.length < limit; i++) {
      var y = spots[i].y;
      if (y < MIN_BEFORE_FIRST || y - last < gap) continue;
      if (height - y < MIN_AFTER_LAST) break;
      chosen.push(spots[i].el);
      last = y;
    }
    if (!chosen.length) return;

    addStyle();
    chosen.forEach(function (el) {
      el.parentNode.insertBefore(makeSlot(), el);
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", place);
  } else {
    place();
  }
})();
