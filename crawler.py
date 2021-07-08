from queue import Queue
import re
import sys
from threading import Event, Lock, Thread
from urllib.parse import urlparse
from urllib.request import urlopen


class Crawler:
    A_RE = re.compile(r"""<a[^>]+href=['"]([^'"]+)['"]""", re.IGNORECASE)

    def __init__(self, uri, workers=4):
        pu = urlparse(uri)

        self.__uris = {}

        self.scheme = pu.scheme
        self.netloc = pu.netloc
        self.netloc_ascii = pu.netloc.encode('idna').decode('ascii')

        self.root = '%s://%s' % (self.scheme, self.netloc_ascii)
        self.start_uri = '%s%s' % (self.root, pu.path or '/')

        self.queue = Queue()
        self.lock = Lock()
        self.run_event = Event()

        self.threads = [
            Thread(target=self.__worker, daemon=True) for _ in range(workers)
        ]

    def crawl(self):
        """Start crawl process"""
        self.__schedule(self.start_uri)
        self.run_event.set()

        try:
            for t in self.threads:
                t.start()

            self.queue.join()

        except KeyboardInterrupt:
            self.queue.queue.clear()
            self.run_event.clear()

            for t in self.threads:
                t.join()

            print('Interrupted.', file=sys.stderr)
            raise

    @property
    def uris(self):
        # TODO: deny mutations
        return self.__uris

    def has(self, uri):
        """Check if url has in crawled urlset"""
        with self.lock:
            return uri in self.__uris

    def is_our(self, uri):
        return uri.startswith(self.start_uri) or uri.startswith('/')

    def normalize(self, uri):
        if uri.startswith('//'):
            uri = '%s:%s' % (self.scheme, uri)
        elif uri.startswith('/'):
            uri = '%s%s' % (self.root, uri)
        # TODO: deal with ./target/path and target/path
        return uri

    def __schedule_crawl(self, html):
        unique_uris = set(self.A_RE.findall(html))
        our_unique_uris = filter(self.is_our, unique_uris)

        for new_uri in map(self.normalize, our_unique_uris):
            if not self.has(new_uri):
                self.__schedule(new_uri)

    def __worker(self):
        while self.run_event.is_set():
            uri = self.queue.get()

            try:
                self.__process(uri)
            except Exception as e:
                print('[E]', uri, repr(e), file=sys.stderr)

            self.queue.task_done()

    def __process(self, uri):
        with urlopen(uri) as response:
            self.__add(uri, response.headers.get('Last-Modified'))
            print(uri)

            self.__schedule_crawl(response.read().decode())

    def __add(self, uri, data = ''):
        with self.lock:
            self.__uris[uri] = data 

    def __schedule(self, uri):
        self.__add(uri)
        self.queue.put_nowait(uri)
