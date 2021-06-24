#!/usr/bin/env python3
'''Generates sitemap.xml by crawl site from base url,
useful to split sitemaps.'''
from configparser import ConfigParser
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
from urllib.request import urlopen

class Crawler:
    A_RE = re.compile(r'<a.*href=\W?(.+?)[\'">\s]')
    def __init__(self, uri):
        pu = urlparse(uri)

        self.uris = {}
        self.netloc = pu.netloc
        self.netloc_ascii = pu.netloc.encode('idna').decode('ascii')
        self.scheme = pu.scheme

        self.start_uri = '%s://%s%s' % (self.scheme, self.netloc_ascii, pu.path or '/')
        self.root = '%s://%s' % (self.scheme, self.netloc_ascii)

    def normalize_uri(self, uri):
        if uri.startswith('//'):
            uri = '%s:%s' % (self.scheme, uri)
        elif uri.startswith('/'):
            uri = '%s%s' % (self.root, uri)
        elif not uri.startswith(self.start_uri):
            return None

        return uri

    def notpassed(self, uri):
        return uri and uri not in self.uris

    def crawl(self, uri=None):
        if not uri:
            uri = self.start_uri
        print(uri)

        with urlopen(uri) as r:
            self.uris[uri] = r.headers.get('Last-Modified')
            c = r.read().decode()
            links = self.A_RE.findall(c)

            normalized_uris = map(self.normalize_uri, set(links))
            for u in filter(self.notpassed, normalized_uris):
                self.crawl(u)


class SitemapGenerator:
    DIR = Path(__file__).resolve().parent
    HEADER = '<?xml version="1.0" encoding="utf-8"?>'
    URLSET_I = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">\n'
    )
    URLSET_O = '</urlset>'
    def __init__(self):
        self.config = ConfigParser()
        self.config.read(self.DIR / 'config.ini')
        self.config['.+'] = {'priority': 0.5}

    def generate(self, uris, file='sitemap.xml', start_uri=''):
        sitemap = self.DIR / file

        config = {
            '%s%s' % (start_uri, p): c for p, c in self.config.items()
        }

        with sitemap.open('w') as s:
            s.write(self.HEADER)
            s.write(self.URLSET_I)
            for uri, lastmod in uris.items():
                for pattern, opts in config.items():
                    if not re.match(pattern, uri):
                        continue
                    s.write('<url>\n')
                    s.write('\t<loc>%s</loc>\n' % uri)
                    changefreq = opts.get('changefreq')
                    priority = float(opts.get('priority', '0.5'))
                    s.write('\t<priority>%1.1f</priority>\n' % priority)
                    if lastmod:
                        s.write('\t<lastmod>%s</lastmod>\n' % lastmod)
                    if changefreq:
                        s.write('\t<changefreq>%s</changefreq>\n' % changefreq)
                    s.write('</url>\n')
                    break
            s.write(self.URLSET_O)



def main(uri, file):
    crawler = Crawler(uri)
    try:
        crawler.crawl()
    except KeyboardInterrupt:
        while True:
            answer = input('Save to %s? (y/n) ' % file).lower()
            if answer not in ('y','n'):
                print('Type y or n.')
                continue
            if answer == 'n':
                sys.exit(130)
            break
    sitemap_generator = SitemapGenerator()
    sitemap_generator.generate(crawler.uris, file, crawler.start_uri)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv)==3 else 'sitemap.xml')
