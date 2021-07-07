#!/usr/bin/env python3
'''Generates sitemap.xml by crawl site from base url,
useful to split sitemaps.'''
from configparser import ConfigParser
from pathlib import Path
from queue import Queue
import re
import sys
from threading import Lock, Thread, Event
from time import sleep
from urllib.parse import urlparse
from urllib.request import urlopen

class Crawler:
    A_RE = re.compile(r'<a.*href=\W?(.+?)[\'">\s]')

    def __init__(self, uri, workers = 4):
        pu = urlparse(uri)

        self.uris = {}

        self.scheme = pu.scheme
        self.netloc = pu.netloc
        self.netloc_ascii = pu.netloc.encode('idna').decode('ascii')

        self.root = '%s://%s' % (self.scheme, self.netloc_ascii)
        self.start_uri = '%s%s' % (self.root, pu.path or '/')

        self.queue = Queue()
        self.lock = Lock()
        self.run_event = Event()

        self.threads = [Thread(target=self.__crawl) for _ in range(workers)]

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
        self._crawl(uri)
        self.run_event.set()
        try:
            for t in self.threads:
                t.daemon = True
                t.start()

            self.queue.join()

        except KeyboardInterrupt:
            self.queue.queue.clear()
            self.run_event.clear()
            
            for t in self.threads:
                t.join()

            print('Interrupted.')
            raise

    def _crawl(self, uri=None):
        if not uri:
            uri = self.start_uri
        self.queue.put(uri)

    def __crawl(self):
        while self.run_event.is_set():
            uri = self.queue.get()
            if self.notpassed(self.normalize_uri(uri)):
                with urlopen(uri) as r:
                    with self.lock:
                        print(uri)
                        self.uris[uri] = r.headers.get('Last-Modified')
                    html = r.read().decode()
                    unique_links = set(self.A_RE.findall(html))

                    normalized_uris = map(self.normalize_uri, unique_links)
                    with self.lock:
                        for u in filter(self.notpassed, normalized_uris):
                            self.queue.put(u)

            self.queue.task_done()


class SitemapGenerator:
    DIR = Path(__file__).resolve().parent
    HEADER = '<?xml version="1.0" encoding="utf-8"?>\n'
    URLSET_I = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    URLSET_O = '</urlset>\n'
    URL_I = '<url>\n'
    URL_O = '</url>\n'

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

                    s.write(self.URL_I)
                    s.write('\t<loc>%s</loc>\n' % uri)
                    changefreq = opts.get('changefreq')
                    priority = float(opts.get('priority', '0.5'))
                    s.write('\t<priority>%1.1f</priority>\n' % priority)
                    if lastmod:
                        s.write('\t<lastmod>%s</lastmod>\n' % lastmod)
                    if changefreq:
                        s.write('\t<changefreq>%s</changefreq>\n' % changefreq)
                    s.write(self.URL_O)
                    break

            s.write(self.URLSET_O)


def main(uri, sitemap_file):
    crawler = Crawler(uri)
    try:
        crawler.crawl()
    except KeyboardInterrupt:
        while True:
            answer = input('Save to %s? (y/n) ' % sitemap_file).lower()
            if answer not in ('y', 'n'):
                print('Type y or n.')
                continue
            if answer == 'n':
                sys.exit(130)
            break
    sitemap_generator = SitemapGenerator()
    sitemap_generator.generate(crawler.uris, sitemap_file, crawler.start_uri)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else 'sitemap.xml')
