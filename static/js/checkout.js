// Client-side checkout validation. The server validates again — this is only
// for faster feedback.
(function () {
  "use strict";
  var form = document.getElementById("checkout-form");
  if (!form) return;

  var rules = {
    full_name: function (v) { return v.trim().length >= 2 || "Enter your full name."; },
    email: function (v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || "Enter a valid email address."; },
    phone: function (v) { return /^(\+977)?9\d{9}$/.test(v.replace(/[\s-]/g, "")) || "Enter a 10-digit Nepali mobile number starting with 9."; },
    address: function (v) { return v.trim().length >= 3 || "Enter where we should deliver or contact you."; },
    city: function (v) { return v.trim().length >= 2 || "Enter your city."; },
  };

  function check(name) {
    var input = form.elements[name];
    var result = rules[name](input.value);
    var msg = result === true ? "" : result;
    var out = form.querySelector('[data-error-for="' + name + '"]');
    if (out) out.textContent = msg;
    input.closest(".field").classList.toggle("has-error", !!msg);
    input.setAttribute("aria-invalid", msg ? "true" : "false");
    return !msg;
  }

  Object.keys(rules).forEach(function (name) {
    var input = form.elements[name];
    if (input) input.addEventListener("blur", function () { check(name); });
  });

  form.addEventListener("submit", function (e) {
    var ok = Object.keys(rules).map(check).every(Boolean);
    if (!ok) {
      e.preventDefault();
      var first = form.querySelector(".has-error input, .has-error textarea");
      if (first) first.focus();
      return;
    }
    var btn = form.querySelector("button");
    btn.disabled = true;
    btn.textContent = "Taking you to eSewa…";
  });
})();
