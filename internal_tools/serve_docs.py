# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Serve the built documentation website, web_docs/, on this computer, and open it in the browser.

    .venv/bin/python internal_tools/serve_docs.py [--port 4173] [--no-browser]

sh user_scripts/launch_docs.sh runs it. web_docs/ is committed, so reading the documents needs no Node.js
and no build: only Python's own web server, answering as GitHub Pages does, under /llamatron/, a page's
address without its .html (VitePress's clean addresses) finding the page. It listens on this computer
alone, and Ctrl+C stops it. internal_tools/build_docs.sh rebuilds web_docs/ after the documents change.
"""

import argparse
import functools
import http.server
import pathlib
import sys
import urllib.parse
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / 'web_docs'
# The site's base, as GitHub Pages serves it and config.mts builds it.
BASE = '/llamatron/'
INDEX = 'index.html'
PAGE_SUFFIX = '.html'
# A name no built file has, which the server answers as not found.
NOT_FOUND = '.not_found'
HOST = '127.0.0.1'
DEFAULT_PORT = 4173
ADDRESS = 'http://localhost:{port}' + BASE
MOVED = 301
LOCATION = 'Location'
CONTENT_LENGTH = 'Content-Length'
NO_BODY = '0'
MSG_SERVING = 'serving the documentation at {address}, Ctrl+C stops it'
MSG_STOPPED = 'stopped'
ERR_NOT_BUILT = 'no website in {folder}: run internal_tools/build_docs.sh first'


def file_for(*, path, root):
    """Return the file under root that a request's path names, or None: the base's index, a page with or without .html, or an asset."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
    if not path.startswith(BASE):
        return None
    inside = path[len(BASE):]
    root = pathlib.Path(root).resolve()
    wanted = (root / inside).resolve()
    if wanted != root and root not in wanted.parents:
        return None
    for candidate in (wanted / INDEX, wanted, wanted.with_name(wanted.name + PAGE_SUFFIX)):
        if candidate.is_file():
            return candidate
    return None


def goes_to_base(path):
    """Whether a request's path is the top of the server, or the base without its last slash, which go to the base."""
    return urllib.parse.urlsplit(path).path in ('/', BASE.rstrip('/'))


class DocsHandler(http.server.SimpleHTTPRequestHandler):
    """Python's file server, finding each file as GitHub Pages does for the site."""

    def do_GET(self):
        if not self.sent_to_base():
            super().do_GET()

    def do_HEAD(self):
        if not self.sent_to_base():
            super().do_HEAD()

    def sent_to_base(self):
        """Send the browser on to the base when the path asks for the top, and say whether it did."""
        if not goes_to_base(self.path):
            return False
        self.send_response(MOVED)
        self.send_header(LOCATION, BASE)
        self.send_header(CONTENT_LENGTH, NO_BODY)
        self.end_headers()
        return True

    def translate_path(self, path):
        found = file_for(path=path, root=self.directory)
        return str(found if found else pathlib.Path(self.directory) / NOT_FOUND)


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='the port to listen on')
    parser.add_argument('--no-browser', action='store_true', help='serve without opening the browser')
    arguments = parser.parse_args(argv)
    if not (SITE / INDEX).is_file():
        print(ERR_NOT_BUILT.format(folder=SITE), file=sys.stderr)
        return 1
    handler = functools.partial(DocsHandler, directory=str(SITE))
    address = ADDRESS.format(port=arguments.port)
    with http.server.ThreadingHTTPServer((HOST, arguments.port), handler) as server:
        print(MSG_SERVING.format(address=address))
        if not arguments.no_browser:
            webbrowser.open(address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print(MSG_STOPPED)
    return 0


if __name__ == '__main__':
    sys.exit(main())
