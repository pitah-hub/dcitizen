/*
  location_map.js: Leaflet map for a request's location.
  data-mode="pick": click the map or drag the pin; the coordinates go into the
                    hidden inputs #id_latitude and #id_longitude.
  data-mode="view": show one fixed pin, read-only.
  If the map library cannot load, the form still works without a pin.
*/
(function () {
  "use strict";

  var el = document.getElementById("location-map");
  if (!el) return;

  if (typeof L === "undefined") {
    el.innerHTML = '<p class="p-3 mb-0 text-secondary">The map could not be loaded. You can still continue without a pin.</p>';
    return;
  }

  var KENYA_CENTRE = [0.0236, 37.9062];
  var mode = el.dataset.mode;
  var lat = parseFloat(el.dataset.lat);
  var lng = parseFloat(el.dataset.lng);
  var hasPin = !isNaN(lat) && !isNaN(lng);

  var map = L.map(el).setView(hasPin ? [lat, lng] : KENYA_CENTRE, hasPin ? 15 : 6);
  // OpenStreetMap's servers refuse tile requests that carry no Referer ("Access blocked").
  // Django's default Referrer-Policy hides it on cross-origin requests, so ask for it here.
  var tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    referrerPolicy: "strict-origin-when-cross-origin",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  if (mode === "view") {
    if (hasPin) L.marker([lat, lng]).addTo(map);
    return;
  }

  /* ---- pick mode ---- */
  var latInput = document.getElementById("id_latitude");
  var lngInput = document.getElementById("id_longitude");
  var status = document.getElementById("location-status");
  var locateBtn = document.getElementById("locate-btn");
  var clearBtn = document.getElementById("clear-pin-btn");
  var marker = null;
  var HINT = "Click the map to drop a pin. You can drag it to adjust.";
  var tileWarned = false;

  tiles.on("tileerror", function () {
    if (tileWarned) return;
    tileWarned = true;
    status.textContent = "The map pictures could not load. You can still click to place a pin, or continue without one.";
  });

  function locateError(err) {
    if (!window.isSecureContext) return "Location only works on a secure (HTTPS) page. Click the map instead.";
    if (err && err.code === 1) return "Location access is blocked. Allow it in the address bar, or click the map instead.";
    if (err && err.code === 3) return "Finding your location took too long. Click the map instead.";
    return "Your device could not work out its location. Click the map instead.";
  }

  function setPin(latlng) {
    if (marker) {
      marker.setLatLng(latlng);
    } else {
      marker = L.marker(latlng, { draggable: true }).addTo(map);
      marker.on("dragend", function () { setPin(marker.getLatLng()); });
    }
    latInput.value = latlng.lat.toFixed(6);
    lngInput.value = latlng.lng.toFixed(6);
    status.textContent = "Pin placed at " + latInput.value + ", " + lngInput.value + ".";
  }

  function clearPin() {
    if (marker) { map.removeLayer(marker); marker = null; }
    latInput.value = "";
    lngInput.value = "";
    status.textContent = HINT;
  }

  map.on("click", function (e) { setPin(e.latlng); });
  clearBtn.addEventListener("click", clearPin);

  if (navigator.geolocation) {
    locateBtn.addEventListener("click", function () {
      status.textContent = "Finding your location...";
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          var here = L.latLng(pos.coords.latitude, pos.coords.longitude);
          setPin(here);
          map.setView(here, 16);
        },
        function (err) { status.textContent = locateError(err); },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  } else {
    locateBtn.hidden = true;
  }

  // Restore the pin when the form is shown again after a validation error.
  if (hasPin) setPin(L.latLng(lat, lng));
  else status.textContent = HINT;

  // Leaflet measures its box on creation; re-measure once the layout has settled.
  setTimeout(function () { map.invalidateSize(); }, 200);
})();
