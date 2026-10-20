(function () {
  "use strict";

  var DEFAULT_IMAGE = { src: "default.svg", v: 0 };

  var slides = [];
  var activeIndex = 0;
  var manifest = normalize(window.XIBO_MANIFEST);
  var currentSrc = null;
  var currentUrl = null;
  var cursorTimer = null;
  var rotateTimer = null;
  var failures = 0;

  function normalize(data) {
    if (!Array.isArray(data)) {
      return [];
    }
    return data.filter(function (entry) {
      return entry && typeof entry.src === "string" && entry.src.length > 0;
    });
  }

  function url(entry) {
    return entry.src + "?v=" + (entry.v || 0);
  }

  function preloadFirst() {
    var first = manifest.length > 0 ? manifest[0] : DEFAULT_IMAGE;
    var link = document.createElement("link");
    link.rel = "preload";
    link.as = "image";
    link.href = url(first);
    link.setAttribute("fetchpriority", "high");
    document.head.appendChild(link);
  }

  function indexOfSrc(list, src) {
    for (var i = 0; i < list.length; i += 1) {
      if (list[i].src === src) {
        return i;
      }
    }
    return -1;
  }

  function present(entry, done) {
    var incoming = slides[1 - activeIndex];
    var outgoing = slides[activeIndex];
    var probe = new Image();
    probe.decoding = "async";
    probe.loading = "eager";
    probe.setAttribute("fetchpriority", "high");

    function fail() {
      failures += 1;
      currentSrc = entry.src;
      done(false);
    }

    probe.onerror = fail;
    probe.onload = function () {
      var ready = typeof probe.decode === "function" ? probe.decode() : Promise.resolve();
      ready.then(function () {
        incoming.src = probe.src;
        incoming.classList.add("visible");
        outgoing.classList.remove("visible");
        activeIndex = 1 - activeIndex;
        currentSrc = entry.src;
        currentUrl = url(entry);
        failures = 0;
        done(true);
      }, fail);
    };
    probe.src = url(entry);
  }

  function schedule(delay) {
    if (rotateTimer !== null) {
      clearTimeout(rotateTimer);
    }
    rotateTimer = setTimeout(advance, delay);
  }

  function advance() {
    var list = manifest.length > 0 ? manifest : [DEFAULT_IMAGE];
    var position = currentSrc === null ? -1 : indexOfSrc(list, currentSrc);
    var next = list[(position + 1) % list.length];

    if (list.length === 1 && currentUrl === url(next)) {
      schedule(REFRESH_MANIFEST_MS);
      return;
    }

    present(next, function (ok) {
      if (ok) {
        schedule(SLIDE_DURATION_MS);
      } else if (failures >= list.length) {
        showFallback();
      } else {
        schedule(250);
      }
    });
  }

  function showFallback() {
    present(DEFAULT_IMAGE, function () {
      schedule(REFRESH_MANIFEST_MS);
    });
  }

  function reloadManifest() {
    var script = document.createElement("script");
    script.src = "manifest.js?t=" + Date.now();
    script.onload = function () {
      var fresh = normalize(window.XIBO_MANIFEST);
      script.remove();
      if (fresh.length === 0 && manifest.length > 0) {
        return;
      }
      var wasEmpty = manifest.length === 0;
      manifest = fresh;
      if (wasEmpty && manifest.length > 0) {
        schedule(0);
      }
    };
    script.onerror = function () {
      script.remove();
    };
    document.head.appendChild(script);
  }

  function showCursor() {
    document.documentElement.classList.add("cursor-visible");
    if (cursorTimer !== null) {
      clearTimeout(cursorTimer);
    }
    cursorTimer = setTimeout(function () {
      document.documentElement.classList.remove("cursor-visible");
    }, CURSOR_HIDE_MS);
  }

  function start() {
    slides = [document.getElementById("slideA"), document.getElementById("slideB")];
    document.addEventListener("mousemove", showCursor, { passive: true });
    document.addEventListener("mousedown", showCursor, { passive: true });
    setInterval(reloadManifest, REFRESH_MANIFEST_MS);
    advance();
  }

  preloadFirst();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
