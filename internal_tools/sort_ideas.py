# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Keep the ideas files sorted by priority: 1 first, then by the order the ideas already have.

    .venv/bin/python internal_tools/sort_ideas.py            # sort .claude/planning/IDEAS.yml in place
    .venv/bin/python internal_tools/sort_ideas.py --check    # say which are out of order, change nothing, and fail if any is

An ideas file is a YAML list of ideas, each with a title, a priority and a text. The user's words for a
priority are numbers there: high is 1, medium is 5, low is 10, and an idea the user hasn't ranked is 99, so
that it sits under every idea that is ranked. The user edits a priority by hand, or moves an idea within its
priority, and this puts the file back in order without undoing the move: ideas of one priority keep the
order they have. The comment lines at the top of a file, which say what the file is, are kept as they are.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'python' / 'src'))
from llamatron_tools.safe_yaml import load_safely  # noqa: E402
IDEAS_FILES = (ROOT / '.claude' / 'planning' / 'IDEAS.yml',)

# The fields of an idea, as the file writes them.
TITLE = 'title'
PRIORITY = 'priority'
TEXT = 'text'
# What the user's words for a priority mean, and the priority of an idea the user hasn't ranked.
HIGH = 1
MEDIUM = 5
LOW = 10
UNRANKED = 99

COMMENT_MARK = '#'
NEW_LINE = '\n'
# How an idea is written: its title in double quotes, its priority, and its text as a block that reads as written.
IDEA_HEAD = '- title: {title}\n  priority: {priority}\n  text: |\n'
TEXT_INDENT = '    '

SORTED = '{path}: sorted'
IN_ORDER = '{path}: in order'
OUT_OF_ORDER = '{path}: out of order'
BAD_IDEA = '{path}: idea {number} needs a title, a whole number as its priority and a text'


class BadIdeasFile(Exception):
    """An ideas file holds something that isn't an idea."""


def header_of(text):
    """Return the comment and blank lines an ideas file starts with, which say what the file is."""
    lines = []
    for line in text.splitlines():
        if line.strip() and not line.startswith(COMMENT_MARK):
            break
        lines.append(line)
    return NEW_LINE.join(lines).strip()


def is_idea(idea):
    return isinstance(idea, dict) and isinstance(idea.get(TITLE), str) and isinstance(idea.get(TEXT), str) and type(idea.get(PRIORITY)) is int


def ideas_of(*, text, path):
    """Return the ideas a file's text holds, refusing anything that isn't one."""
    ideas = load_safely(text) or []
    for number, idea in enumerate(ideas, start=1):
        if not is_idea(idea):
            raise BadIdeasFile(BAD_IDEA.format(path=path, number=number))
    return ideas


def priority_of(idea):
    return idea[PRIORITY]


def in_order(ideas):
    """Return the ideas with the lowest priority number first, those of one priority in the order they had."""
    return sorted(ideas, key=priority_of)


def text_block(text):
    """Return an idea's text as the lines of a YAML block, indented, with no line ending in a space."""
    lines = [(TEXT_INDENT + line).rstrip() for line in text.strip().splitlines()]
    return NEW_LINE.join(lines) + NEW_LINE


def written_idea(idea):
    head = IDEA_HEAD.format(title=json.dumps(idea[TITLE], ensure_ascii=False), priority=idea[PRIORITY])
    return head + text_block(idea[TEXT])


def written(*, header, ideas):
    """Return an ideas file's text: the header, then every idea, a blank line between."""
    parts = [header + NEW_LINE] if header else []
    parts.extend(written_idea(idea) for idea in ideas)
    return NEW_LINE.join(parts)


def sorted_text(*, text, path):
    """Return an ideas file's text with its ideas in order."""
    return written(header=header_of(text), ideas=in_order(ideas_of(text=text, path=path)))


def is_in_order(*, text, path):
    ideas = ideas_of(text=text, path=path)
    return ideas == in_order(ideas)


def main(*, argv=None, paths=IDEAS_FILES):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='say which files are out of order and change nothing')
    arguments = parser.parse_args(argv)
    failed = False
    for path in paths:
        text = Path(path).read_text()
        try:
            ordered = is_in_order(text=text, path=path)
            if arguments.check:
                print((IN_ORDER if ordered else OUT_OF_ORDER).format(path=path))
                failed = failed or not ordered
                continue
            new = sorted_text(text=text, path=path)
        except BadIdeasFile as error:
            print(error, file=sys.stderr)
            failed = True
            continue
        if new != text:
            Path(path).write_text(new)
        print((IN_ORDER if ordered else SORTED).format(path=path))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
