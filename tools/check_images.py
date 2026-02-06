#!/usr/bin/env python3
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin
import urllib.request

import os

HOST = os.environ.get('HOST', 'http://127.0.0.1:5000')
PAGES = ['/', '/shop']

class ImgCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.imgs = []
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'img':
            self.imgs.append(attrs)
        if tag.lower() == 'script':
            src = attrs.get('src')
            if src:
                self.scripts.append(src)


def head_status(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.getcode(), resp.getheader('Content-Type')
    except Exception as e:
        # Try GET small
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.getcode(), resp.getheader('Content-Type')
        except Exception as e2:
            return None, str(e2)


def check_page(path):
    url = urljoin(HOST, path)
    print('---')
    print('Page:', url)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print('ERROR fetching page:', e)
        return
    parser = ImgCollector()
    parser.feed(html)
    print('Found images:', len(parser.imgs))
    missing_fallback = []
    errors = []
    for i, attrs in enumerate(parser.imgs, 1):
        src = attrs.get('src') or attrs.get('data-src') or ''
        fallback = attrs.get('data-fallback') or attrs.get('data-placeholder') or ''
        abs_src = urljoin(HOST, src) if src else ''
        abs_fallback = urljoin(HOST, fallback) if fallback else ''
        print(f'[{i}] src={src} fallback={fallback}')
        if src:
            code, ctype = head_status(abs_src)
            print('    src status:', code, ctype)
            if code is None or (isinstance(code,int) and code>=400):
                errors.append((src, code))
        else:
            print('    src missing')
        if fallback:
            code2, ctype2 = head_status(abs_fallback)
            print('    fallback status:', code2, ctype2)
            if code2 is None or (isinstance(code2,int) and code2>=400):
                missing_fallback.append((fallback, code2))
        else:
            print('    fallback missing')
    # check for image-fallbacks script
    found_fallback_script = any(('fallback' in s.lower()) or ('image' in s.lower() and 'fallback' in s.lower()) for s in parser.scripts)
    print('Scripts found:', len(parser.scripts))
    print('Sample scripts:', parser.scripts[:10])
    print('Image-fallback script present (heuristic):', found_fallback_script)
    if errors:
        print('\nImages with bad src:')
        for it in errors:
            print(' -', it)
    if missing_fallback:
        print('\nMissing/unavailable fallback files:')
        for it in missing_fallback:
            print(' -', it)

if __name__ == '__main__':
    for p in PAGES:
        check_page(p)
    print('---\nDone')
