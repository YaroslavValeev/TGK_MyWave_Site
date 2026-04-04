(function () {
  const box = document.getElementById("mw-latest-post");
  if (!box) return;

  const hasServer = box.dataset.hasServer === "1";
  if (hasServer) return;

  fetch("/api/blog/latest", { headers: { "Accept": "application/json" } })
    .then((r) => r.ok ? r.json() : Promise.reject(r))
    .then((data) => {
      if (!data || !data.slug) return;

      const title = data.title || "Последняя новость";
      const lead = data.lead || "";
      const publishedAt = data.published_at ? new Date(data.published_at) : null;

      const dateStr = publishedAt && !isNaN(publishedAt.getTime())
        ? publishedAt.toLocaleDateString("ru-RU")
        : "";

      const href = `/blog/${encodeURIComponent(data.slug)}?src=latest`;

      box.innerHTML = `
        <a class="mw-latest-post__link" href="${href}">
          <div class="mw-latest-post__meta">
            <div class="mw-latest-post__title"></div>
            ${lead ? `<div class="mw-latest-post__lead"></div>` : ""}
            ${dateStr ? `<div class="mw-latest-post__date">${dateStr}</div>` : ""}
          </div>
        </a>
      `;

      box.querySelector(".mw-latest-post__title").textContent = title;
      if (lead) box.querySelector(".mw-latest-post__lead").textContent = lead;
    })
    .catch(() => {
      // молча — блок уже показывает "Загружаем…"
    });
})();

