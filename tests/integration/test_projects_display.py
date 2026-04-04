"""Верификация отображения страницы /projects: карточки, обложки, структура."""
import pytest
from bs4 import BeautifulSoup

from app import create_app


def test_projects_page_renders_cards():
    app = create_app(config_name='testing')
    client = app.test_client()

    resp = client.get('/projects')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'projects-carousel' in html
    assert 'project-card' in html

    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('.project-card')
    assert len(cards) >= 1

    for card in cards:
        img = card.find('img', class_='project-card__cover')
        assert img, "у каждой карточки должна быть обложка с классом project-card__cover"
        assert img.get('src'), "у обложки должен быть src"
        assert img.get('data-fallback'), "у обложки должен быть data-fallback для onerror"


def test_projects_page_cards_have_consistent_structure():
    """Проверка единой структуры: заголовок, описание, actions."""
    app = create_app(config_name='testing')
    client = app.test_client()
    resp = client.get('/projects')
    soup = BeautifulSoup(resp.get_data(as_text=True), 'html.parser')

    for card in soup.select('.project-card'):
        assert card.select_one('.project-card__title, h4'), "заголовок"
        assert card.select_one('.project-card__summary'), "описание"
        assert card.select_one('.project-card__actions'), "блок действий"
