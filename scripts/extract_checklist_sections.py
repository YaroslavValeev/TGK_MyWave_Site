# -*- coding: utf-8 -*-
"""Извлекает блок checklist-content в отдельный файл и заменяет его на include."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKLIST_HTML = os.path.join(BASE, "templates", "wake_industry", "checklist.html")
SECTIONS_HTML = os.path.join(BASE, "templates", "wake_industry", "checklist_sections.html")

def main():
    with open(CHECKLIST_HTML, "r", encoding="utf-8") as f:
        text = f.read()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    start_marker = '<section class="mw-section" id="checklist-content">'
    i = text.find(start_marker)
    if i == -1:
        raise SystemExit("start_marker not found")
    j_endblock = text.find("{% endblock %}", i)
    if j_endblock == -1:
        raise SystemExit("{% endblock %} not found after start_marker")
    # Последний </section> перед {% endblock %} (закрывает блок checklist-content)
    chunk_before = text[i:j_endblock]
    j_close = chunk_before.rfind("\n</section>")
    if j_close == -1:
        raise SystemExit("</section> not found before {% endblock %}")
    j = i + j_close  # позиция начала \n</section> в text
    # Контент секции включая закрывающий тег </section>
    section_content = text[i : j + len("\n</section>")]
    with open(SECTIONS_HTML, "w", encoding="utf-8") as f:
        f.write(section_content)
    # Заменяем блок на include; после </section> идёт \n\n{% endblock %}...
    end_len = len("\n</section>")
    new_text = text[:i] + '{% include "wake_industry/checklist_sections.html" %}' + "\n\n" + text[j + end_len:]
    with open(CHECKLIST_HTML, "w", encoding="utf-8") as f:
        f.write(new_text)
    with open(log_path, "w", encoding="utf-8") as log:
        log.write("OK: sections len=%d checklist updated\n" % len(section_content))
    print("OK: sections extracted, checklist.html updated")

if __name__ == "__main__":
    main()
