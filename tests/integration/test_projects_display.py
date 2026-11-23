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


def test_projects_page_includes_spotmap_card():
    """SpotMap — 3-я карточка в карусели; обложка карты; iframe ленивый."""
    app = create_app(config_name='testing')
    client = app.test_client()
    resp = client.get('/projects')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="spotmap"' in html
    assert 'project-card--spotmap' in html
    assert 'map.mywavewake.ru/embed' in html
    assert 'host=mywave' in html
    assert 'spotmap-section' not in html
    assert 'spotmap_cover.webp' in html
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('.projects-carousel .project-card')
    assert len(cards) >= 3
    # 3-я по счёту (index 2)
    assert 'project-card--spotmap' in (cards[2].get('class') or [])
    card = soup.select_one('#spotmap.project-card--spotmap')
    assert card is not None
    cover = card.select_one('.project-card__cover')
    assert cover is not None
    assert 'spotmap_cover.webp' in (cover.get('src') or '')
    assert card.select_one('.project-card__summary')
    assert card.select_one('.project-card__actions')
    iframe = card.select_one('iframe[data-spotmap-src]')
    assert iframe is not None
    assert 'map.mywavewake.ru/embed' in iframe.get('data-spotmap-src', '')
    assert iframe.get('src') in (None, '')
    assert iframe.get('allow') == 'geolocation'


def test_home_page_includes_spotmap_third():
    """На главной SpotMap видна 3-й карточкой в блоке Проекты."""
    app = create_app(config_name='testing')
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'project-card--spotmap' in html
    assert 'spotmap_cover.webp' in html
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('#projects .projects-carousel .project-card')
    assert len(cards) >= 3
    assert 'project-card--spotmap' in (cards[2].get('class') or [])
