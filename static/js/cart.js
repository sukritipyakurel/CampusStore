// Client-side cart interactions: add / update / remove without a page reload.
// Every form still works without JavaScript (plain POST + redirect).
(function () {
  "use strict";

  function post(form) {
    return fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "application/json" },
      credentials: "same-origin",
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
        return data;
      });
    });
  }

  function updateBadges(data) {
    document.querySelectorAll("[data-cart-count]").forEach(function (el) {
      el.textContent = data.cart_count;
      el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump");
    });
    document.querySelectorAll("[data-cart-total]").forEach(function (el) {
      el.textContent = data.cart_total;
    });
  }

  // Product page: "Add to cart"
  document.querySelectorAll("[data-ajax-add]").forEach(function (form) {
    var status = form.querySelector("[data-add-status]");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      post(form).then(function (data) {
        updateBadges(data);
        status.innerHTML = 'Added. You have ' + data.quantity + ' in your cart. <a href="/cart/">View cart</a>';
      }).catch(function (err) { status.textContent = err.message; });
    });
  });

  // Cart page: quantity change
  document.querySelectorAll("[data-ajax-qty]").forEach(function (form) {
    var input = form.querySelector("input[name=quantity]");
    var timer;
    form.addEventListener("submit", function (e) { e.preventDefault(); });
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        var max = parseInt(input.max, 10), val = parseInt(input.value, 10);
        if (!val || val < 1) return;
        if (max && val > max) input.value = max;
        post(form).then(function (data) {
          updateBadges(data);
          input.value = data.quantity;
          form.closest("tr").querySelector("[data-line-total]").textContent = "Rs. " + data.line_total;
        });
      }, 350);
    });
  });

  // Cart page: remove
  document.querySelectorAll("[data-ajax-remove]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      post(form).then(function (data) {
        updateBadges(data);
        form.closest("tr").remove();
        if (data.cart_count === 0) window.location.reload();
      });
    });
  });

  // Sort dropdowns submit on change
  document.querySelectorAll("[data-autosubmit]").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form.submit(); });
  });
})();
