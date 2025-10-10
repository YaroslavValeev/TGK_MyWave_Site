fetch('/faq.json')
  .then(response => response.json())
  .then(data => {
    const faqList = data.faq || data;
    const accordion = document.getElementById('faqAccordion');
    while (accordion && accordion.firstChild) accordion.removeChild(accordion.firstChild);
    faqList.forEach((item, index) => {
      const question = item.script_id || '';
      const answer = item.script_name || '';
      const card = document.createElement('div');
      card.className = 'card mb-2';

      const header = document.createElement('div');
      header.className = 'card-header';
      header.id = `heading${index}`;

      const h2 = document.createElement('h2');
      h2.className = 'mb-0';

      const button = document.createElement('button');
      button.className = 'btn btn-link btn-block text-left';
      button.type = 'button';
      button.setAttribute('data-toggle', 'collapse');
      button.setAttribute('data-target', `#collapse${index}`);
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-controls', `collapse${index}`);
      button.textContent = question;

      h2.appendChild(button);
      header.appendChild(h2);

      const collapse = document.createElement('div');
      collapse.id = `collapse${index}`;
      collapse.className = 'collapse';
      collapse.setAttribute('aria-labelledby', `heading${index}`);
      collapse.setAttribute('data-parent', '#faqAccordion');

      const body = document.createElement('div');
      body.className = 'card-body';
      // answer may contain simple HTML — escape to text to be safe
      body.textContent = answer;

      collapse.appendChild(body);
      card.appendChild(header);
      card.appendChild(collapse);
      accordion.appendChild(card);
    });
  })
  .catch(error => {
    const acc = document.getElementById('faqAccordion');
    if (acc) {
      while (acc.firstChild) acc.removeChild(acc.firstChild);
      const p = document.createElement('p');
      p.textContent = 'Ошибка загрузки FAQ.';
      acc.appendChild(p);
    }
    console.error('Ошибка загрузки FAQ:', error);
  });

// Поиск по вопросам
const searchInput = document.getElementById('faqSearch');
searchInput.addEventListener('input', e => {
  const filter = e.target.value.toLowerCase();
  document.querySelectorAll('#faqAccordion .card').forEach(card => {
    const q = card.querySelector('.card-header').innerText.toLowerCase();
    card.style.display = q.includes(filter) ? '' : 'none';
  });
}); 