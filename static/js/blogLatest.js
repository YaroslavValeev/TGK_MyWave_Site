fetch("/static/data/blog_posts.json")
  .then(res => res.json())
  .then(posts => {
    const latest = posts[0];
    const block = document.getElementById("latest-news");
    if (block && latest) {
      block.innerHTML = `
        <h3>${latest.title}</h3>
        <p><em>${latest.date}</em></p>
        <p>${latest.content}</p>
      `;
    }
  })
  .catch(err => {
    console.warn("Ошибка загрузки новостей:", err);
  });
