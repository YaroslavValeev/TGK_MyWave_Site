#!/usr/bin/env python3
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin
import urllib.request
import yaml

HOST = os.environ.get('HOST', 'http://127.0.0.1:5001')

class CardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_project = False
        self.curr = {}
        self.cards = []
        self.tag_stack = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tag_stack.append(tag)
        if tag == 'li' and ('class' in attrs and 'project-card' in attrs['class']):
            self.in_project = True
            self.curr = {'type': 'project'}
        if self.in_project and tag == 'img' and 'alt' in attrs:
            self.curr['alt'] = attrs.get('alt')
        if self.in_project and tag in ('h2','h3','h4'):
            self.curr['last_tag'] = tag
            self.curr.setdefault('texts', []).append('')
    def handle_endtag(self, tag):
        if self.tag_stack:
            self.tag_stack.pop()
        if tag == 'li' and self.in_project:
            self.in_project = False
            self.cards.append(self.curr)
            self.curr = {}
    def handle_data(self, data):
        if self.in_project and self.curr.get('last_tag'):
            if self.curr['texts']:
                self.curr['texts'][-1] += data.strip()


def fetch_and_parse(path='/'):
    url = urljoin(HOST, path)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print('ERROR fetching', url, e)
        return []
    p = CardParser()
    p.feed(html)
    return p.cards

if __name__ == '__main__':
    pages = ['/', '/shop', '/projects']
    all_cards = {}
    for p in pages:
        cards = fetch_and_parse(p)
        all_cards[p] = cards
    out = 'card_texts_source_of_truth.yaml'
    with open(out, 'w', encoding='utf-8') as f:
        yaml.safe_dump(all_cards, f, allow_unicode=True)
    print('Wrote', out)
