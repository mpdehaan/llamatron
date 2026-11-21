# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Show the start screen on its own, to look at it, or with --batch a batch video's opening: the title on black, then Arrange with the READY box, cut to black where the song would start.

    .venv/bin/python internal_tools/demo_splash_screen.py [--seconds 5]
    .venv/bin/python internal_tools/demo_splash_screen.py --batch [examples/by_genre/ragtime/entertainer.yml] [--visualizer spectrum]
    .venv/bin/python internal_tools/demo_splash_screen.py --scroll-text ['DEMO: Hocket Shanty']

internal_tools/demo_splash_screen.sh runs it. --seconds is how long the finished title holds, with its
prompt pulsing, after the letters, the scanner and the address have come in. With --batch it opens the
set named, the Entertainer unless told, as a batch video would (tui/batch_stage.py), and quits once READY
has shown. With --scroll-text the title is followed by what a recording shows next, words crossing the
screen: the words given, or the Entertainer's, DEMO: ENTERTAINER, as a recording of that set would show.
Nothing is played, recorded or saved.
"""

import argparse
import sys

from llamatron.tui.app import LlamatronApp
from llamatron.tui.components.scroll_text import scroll_text_for
from llamatron.tui.components.title_card import scan_end
from llamatron.tui.document import Document
from llamatron.tui.launch import Launch

DEFAULT_HOLD_SECONDS = 5.0
DEFAULT_SET = 'examples/by_genre/ragtime/entertainer.yml'
DEFAULT_VISUALIZER = 'cycle'
OPTIONAL = '?'
NO_LEAD_IN = 0.0


def launch_for(*, hold_seconds, scroll_text=None):
    """Return the launch that shows the start screen until it has come in and held for hold_seconds, then the words that scroll when there are any, and quits."""
    return Launch(test_splash=True, splash_seconds=scan_end() + hold_seconds, lead_in_seconds=NO_LEAD_IN, scroll_text=scroll_text)


def opening_launch(*, visualizer):
    """Return the launch that plays a batch video's opening and stops where the song would start."""
    return Launch(batch_video=True, opening_only=True, visualizer=visualizer)


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--seconds', type=float, default=DEFAULT_HOLD_SECONDS, help='how long the finished title holds before it fades out')
    parser.add_argument('--batch', nargs=OPTIONAL, const=DEFAULT_SET, default=None, help="a batch video's opening on this set, the Entertainer unless named")
    parser.add_argument('--visualizer', default=DEFAULT_VISUALIZER, help='the mode the batch video would show')
    parser.add_argument('--scroll-text', nargs=OPTIONAL, const=scroll_text_for(DEFAULT_SET), default=None, help="after the title, these words crossing the screen as a recording shows a demo's name, the Entertainer's unless given")
    arguments = parser.parse_args(argv)
    if arguments.batch is None:
        LlamatronApp(launch=launch_for(hold_seconds=arguments.seconds, scroll_text=arguments.scroll_text)).run()
        return 0
    document, _ = Document.load_or_correct(arguments.batch)
    LlamatronApp(document=document, launch=opening_launch(visualizer=arguments.visualizer)).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
