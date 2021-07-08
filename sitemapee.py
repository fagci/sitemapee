#!/usr/bin/env python3
'''Generates sitemap.xml by crawl site from base url,
useful to split sitemaps.'''
from argparse import ArgumentParser
import sys

from crawler import Crawler
from sitemap_generator import SitemapGenerator

# TODO: deal with robots.txt


def main(uri, sitemap_file, w=4):
    crawler = Crawler(uri, w)

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
    ap = ArgumentParser(description='SitemapGenerator')
    ap.add_argument('uri', help='Root uri to parse from and constrain to')
    ap.add_argument('-o', default='sitemap.xml', help='Output xml file')
    ap.add_argument('-w', default=4, type=int, help='Workers count')
    args = ap.parse_args()
    main(args.uri, args.o, args.w)
