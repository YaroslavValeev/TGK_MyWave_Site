(function () {
  var toggle = document.getElementById("admin-sidebar-toggle");
  var sidebar = document.getElementById("admin-sidebar");
  var overlay = document.getElementById("admin-overlay");

  if (!toggle || !sidebar || !overlay) {
    return;
  }

  function closeSidebar() {
    sidebar.classList.remove("is-open");
    overlay.classList.remove("is-visible");
  }

  function openSidebar() {
    sidebar.classList.add("is-open");
    overlay.classList.add("is-visible");
  }

  toggle.addEventListener("click", function () {
    if (sidebar.classList.contains("is-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  overlay.addEventListener("click", closeSidebar);
})();
