/*
  modern.js: small interaction layer. No libraries, no build step.
  Every effect degrades to the plain page if JavaScript or motion is unavailable.
  Opt a card IN to tilt with class "tilt", OUT with class "no-tilt".
*/
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var hasObserver = "IntersectionObserver" in window;

  /* ---- 1. 3D tilt on small grid cards (service cards, stat cards) ---- */
  function initTilt() {
    if (reduceMotion || !canHover) return;
    var MAX_DEG = 7;
    var skip = "form, table, canvas, input, select, textarea";

    document.querySelectorAll(".card").forEach(function (card) {
      if (card.closest(".no-tilt") || card.querySelector(skip)) return;

      var box = card.getBoundingClientRect();
      var inGrid = !!card.closest('[class*="col"]');
      var smallEnough = box.width <= 480 && box.height <= 320;
      if (!card.classList.contains("tilt") && !(inGrid && smallEnough)) return;

      card.classList.add("is-tilt");

      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width;
        var y = (e.clientY - r.top) / r.height;
        card.style.setProperty("--ry", ((x - 0.5) * 2 * MAX_DEG).toFixed(2) + "deg");
        card.style.setProperty("--rx", ((0.5 - y) * 2 * MAX_DEG).toFixed(2) + "deg");
        card.style.setProperty("--mx", (x * 100).toFixed(1) + "%");
        card.style.setProperty("--my", (y * 100).toFixed(1) + "%");
        card.classList.add("is-hovering");
      });

      card.addEventListener("pointerleave", function () {
        card.classList.remove("is-hovering");
        card.style.setProperty("--rx", "0deg");
        card.style.setProperty("--ry", "0deg");
      });
    });
  }

  /* ---- 2. Scroll reveal, staggered within a row ---- */
  function initReveal() {
    if (reduceMotion || !hasObserver) return;
    var targets = document.querySelectorAll(".card, .table-responsive, .alert");
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        io.unobserve(el);
        el.classList.add("is-visible");
        // Drop the helper classes afterwards so the element's normal hover
        // transitions are not overridden by the reveal transition.
        setTimeout(function () { el.classList.remove("reveal", "is-visible"); }, 1200);
      });
    }, { threshold: 0.12 });

    targets.forEach(function (el) {
      if (el.closest(".navbar")) return;
      var unit = el.closest('[class*="col"]') || el;
      var index = unit.parentElement ? Array.prototype.indexOf.call(unit.parentElement.children, unit) : 0;
      el.style.setProperty("--d", (index % 6) * 70 + "ms");
      el.classList.add("reveal");
      io.observe(el);
    });
  }

  /* ---- 3. Count-up for plain numbers in stat cards ---- */
  function initCounters() {
    if (reduceMotion || !hasObserver) return;
    var selector = ".card h1, .card h2, .card h3, .card .display-4, .card .display-5, .card .display-6, [data-count]";
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        io.unobserve(entry.target);
        countUp(entry.target);
      });
    }, { threshold: 0.4 });

    document.querySelectorAll(selector).forEach(function (el) {
      if (el.children.length || el.closest("table")) return;
      var raw = el.dataset.count !== undefined ? el.dataset.count : el.textContent.trim();
      if (!/^\d{1,6}$/.test(raw)) return;
      el.dataset.target = raw;
      el.classList.add("stat-number");
      io.observe(el);
    });
  }

  function countUp(el) {
    var target = parseInt(el.dataset.target, 10);
    if (!target) return;
    var duration = 900;
    var start = null;
    function frame(now) {
      if (start === null) start = now;
      var t = Math.min((now - start) / duration, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased);
      if (t < 1) requestAnimationFrame(frame);
    }
    el.textContent = "0";
    requestAnimationFrame(frame);
  }

  /* ---- 4. Navbar shadow once the page scrolls ---- */
  function initNavbar() {
    var nav = document.querySelector(".navbar");
    if (!nav) return;
    function update() { nav.classList.toggle("is-scrolled", window.scrollY > 8); }
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  /* ---- 5. Submit button spinner, blocks accidental double submits ---- */
  function initSubmitState() {
    document.querySelectorAll("form").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        // A <button> with no type attribute is a submit button too.
        var btn = form.querySelector(
          'button:not([type]):not([data-no-loading]), button[type="submit"]:not([data-no-loading]), input[type="submit"]:not([data-no-loading])'
        );
        if (!btn || btn.disabled) return;
        // Deferred so the browser still sends the form before the button is disabled,
        // and so a form that another handler cancelled is not left locked.
        setTimeout(function () {
          if (event.defaultPrevented) return;
          btn.disabled = true;
          btn.classList.add("is-loading");
        }, 0);
      });
    });
    // Back button restores the page from cache: undo the loading state.
    window.addEventListener("pageshow", function (e) {
      if (!e.persisted) return;
      document.querySelectorAll(".btn.is-loading").forEach(function (b) {
        b.disabled = false;
        b.classList.remove("is-loading");
      });
    });
  }

  function init() {
    initNavbar();
    initSubmitState();
    initTilt();
    initReveal();
    initCounters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();