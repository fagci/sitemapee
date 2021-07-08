from configparser import ConfigParser
from pathlib import Path
import re


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

        config = {'%s%s' % (start_uri, p): c for p, c in self.config.items()}

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
