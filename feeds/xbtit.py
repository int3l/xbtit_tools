import argparse
import re
import urllib
from contextlib import redirect_stdout
from sys import stderr
from sys import stdout
from time import sleep

import feedparser

from utils.cache import LRU
from utils.config import cache_limit
from utils.config import parser_config


TITLE_PATTERN = re.compile(r'\[.*?\] (?P<title>.*?) \[SEEDERS.*\]')
TORRENT_URL_PATTERN = re.compile(
    r'^(?P<href>http://.*/download\.php\?id=[a-z0-9]{30,40}\&'
    r'f=[a-zA-Z0-9%.-]{1,600}\.torrent&rsspid=[a-z0-9]{30,40})$',
)


def extract_title(title):
    title_match = TITLE_PATTERN.search(title)
    if title_match:
        return title_match.group('title').strip()
    else:
        print(f'Bad title {title}')


def extract_url(enclosures):
    if not enclosures or enclosures[0].type != 'application/x-bittorrent':
        print(f'Bad enclosures {enclosures}')
        return

    url_match = TORRENT_URL_PATTERN.search(enclosures[0].href)
    if url_match:
        return url_match.group('href')
    else:
        print(f'Bad URL {enclosures[0].href}')


def tracker():
    try:
        rss = feedparser.parse(**parser_config())
    except urllib.error.URLError:
        print('Retrying ...')
        return

    if rss.status != 200 or rss.bozo != 0:
        print(f'Bad status {rss.status}, bozo {rss.bozo}')
        print(f'Bad {rss.bozo_exception}')
        return

    for entry in reversed(rss.entries):
        yield (
            entry.id,
            extract_title(entry.title),
            extract_url(entry.enclosures),
        )


def rss_feed(args):
    last_torrents = LRU(cache_limit(), [(tid, None) for tid, *_ in tracker()])

    while True:
        sleep(5)
        for tid, title, url in tracker():
            if tid in last_torrents or not title or not url:
                continue
            elif args.url:
                print(f'{title}\0{url}', file=stdout, flush=True)
            else:
                print(title, file=stdout, flush=True)


def _main():
    parser = argparse.ArgumentParser(prog='xbtit_feed')
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version='%(prog)s 0.0.1',
    )
    parser.add_argument('-u', '--url', action='store_true')
    args = parser.parse_args()

    with redirect_stdout(stderr):
        rss_feed(args)


def main():
    try:
        exit(_main())
    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == '__main__':
    main()
