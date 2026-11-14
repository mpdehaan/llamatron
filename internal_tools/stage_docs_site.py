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

"""Stage llamatron's guide and its chapters for the documentation website, which VitePress builds into web_docs/.

    .venv/bin/python internal_tools/stage_docs_site.py --out .docs_site/site

internal_tools/build_docs.sh runs it before each build. It copies GUIDE.md as the site's front page,
index.md, every chapter in docs/ beside it, in the subfolders docs/ has them in, and docs/screenshots/,
rewriting the links to the guide: the guide's docs/X.md becomes X.md, and a chapter's ../GUIDE.md becomes
index.md (../../GUIDE.md becoming ../index.md a folder down). It writes sidebar.json, the site's sidebar, from
the guide's own tables of chapters, in their order: each chapter a page of its own, except that the tables
under the headings GROUPED names make groups that open and close, the user's design, a group opening the page of
its own name and a ### heading making a group within a group.
So the site lists exactly what the guide does, and the guide stays the one place a chapter is added. The Markdown
in docs/ and GUIDE.md is never changed; the staging folder is built afresh each time, and git ignores it.
"""

import argparse
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GUIDE = ROOT / 'GUIDE.md'
DOCS = ROOT / 'docs'
SCREENSHOTS = 'screenshots'
INDEX = 'index.md'
SIDEBAR = 'sidebar.json'
CHAPTER_FILES = '*.md'
ENCODING = 'utf-8'
# The links the site's one folder needs in place of the repository's.
GUIDE_TO_CHAPTER = '](docs/'
SAME_FOLDER = ']('
CHAPTER_TO_GUIDE = ']({up}GUIDE.md'
TO_INDEX = ']({up}index.md'
UP = '../'
# The guide's tables of chapters: a row's first link to a chapter names it, and a heading starts each table's group.
CHAPTER_LINK = re.compile(r'\[([^\]]+)\]\(docs/([A-Za-z_/]+)\.md\)')
HEADING = re.compile(r'^## (.+)$')
SUBHEADING = re.compile(r'^### (.+)$')
TABLE_ROW = '|'
TABLE_RULE = '| ---'
# What the sidebar calls the front page and its group.
FRONT_PAGE_ITEM = 'Home'
# The guide's headings whose tables make a group of the sidebar, which opens and closes, rather than pages of their own.
GROUPED = ('Intro', 'Demo Songs', 'Objects', 'Generators', 'File Operations', 'MIDI & Performance', 'Advanced')
FRONT_PAGE_LINK = '/'
CHAPTER_PAGE_LINK = '/{name}'
# The keys of VitePress's sidebar.
TEXT = 'text'
ITEMS = 'items'
COLLAPSED = 'collapsed'
HIDDEN = '.'
MARKDOWN = '.md'
LINK = 'link'
MSG_STAGED = 'staged {count} pages into {folder}'


def site_guide(text):
    """Return the guide as the site's front page, its links to docs/ made links beside it."""
    return text.replace(GUIDE_TO_CHAPTER, SAME_FOLDER)


def site_chapter(*, text, depth=0):
    """Return a chapter as the site shows it, its links to the guide made links to the front page; depth is how many folders below docs/ it lies, as the site keeps them."""
    return text.replace(CHAPTER_TO_GUIDE.format(up=UP * (depth + 1)), TO_INDEX.format(up=UP * depth))


def sidebar(guide_text):
    """Return the site's sidebar from the guide's tables of chapters, in the guide's order, each chapter once.

    The front page comes first. A table under a heading GROUPED doesn't name lists pages of their own;
    the tables under a heading it names make a group of that name that opens and closes, which opens
    the page of the same name when the group's first chapter is it, and a ### heading inside such a group
    makes a group within it, the user's design; a group within one opens the page of its own name when its first chapter is
    it, and a group within one that holds only that chapter is the chapter alone.
    """
    entries = [{TEXT: FRONT_PAGE_ITEM, LINK: FRONT_PAGE_LINK}]
    group = None
    subgroup = None
    seen = set()
    for line in guide_text.splitlines():
        top = HEADING.match(line)
        if top:
            group = None
            subgroup = None
            if top.group(1) in GROUPED:
                group = {TEXT: top.group(1), COLLAPSED: False, ITEMS: []}
                entries.append(group)
            continue
        inner = SUBHEADING.match(line)
        if inner and group is not None:
            subgroup = {TEXT: inner.group(1), COLLAPSED: False, ITEMS: []}
            group[ITEMS].append(subgroup)
            continue
        if not line.startswith(TABLE_ROW) or line.startswith(TABLE_RULE):
            continue
        for title, name in CHAPTER_LINK.findall(line):
            if name in seen:
                continue
            seen.add(name)
            item = {TEXT: title, LINK: CHAPTER_PAGE_LINK.format(name=name)}
            if group is None:
                entries.append(item)
            elif subgroup is not None:
                if title == subgroup[TEXT] and not subgroup[ITEMS] and LINK not in subgroup:
                    subgroup[LINK] = item[LINK]
                else:
                    subgroup[ITEMS].append(item)
            elif title == group[TEXT] and not group[ITEMS] and LINK not in group:
                group[LINK] = item[LINK]
            else:
                group[ITEMS].append(item)
    return [with_single_pages(entry) for entry in entries]


def with_single_pages(entry):
    """Return a sidebar entry with every group inside it that holds only the page of its own name made that page alone, so that a ### heading over one chapter reads as the chapter."""
    if ITEMS not in entry:
        return entry
    items = [with_single_pages(item) for item in entry[ITEMS]]
    items = [{TEXT: item[TEXT], LINK: item[LINK]} if ITEMS in item and not item[ITEMS] and LINK in item else item for item in items]
    return {**entry, ITEMS: items}


def chapter_paths():
    """Return every chapter in docs/, its subfolders' too."""
    return sorted(DOCS.rglob(CHAPTER_FILES))


def stage(*, out):
    """Build the staging folder afresh: the front page, every chapter in the folders it has in docs/, the screenshots and the sidebar. Return how many pages it holds."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for item in out.iterdir():
        if item.name.startswith(HIDDEN):
            continue
        if item.is_dir():
            shutil.rmtree(item)
        elif item.suffix == MARKDOWN:
            item.unlink()
    guide = GUIDE.read_text(encoding=ENCODING)
    (out / INDEX).write_text(site_guide(guide), encoding=ENCODING)
    chapters = chapter_paths()
    for chapter in chapters:
        relative = chapter.relative_to(DOCS)
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(site_chapter(text=chapter.read_text(encoding=ENCODING), depth=len(relative.parts) - 1), encoding=ENCODING)
    shutil.copytree(DOCS / SCREENSHOTS, out / SCREENSHOTS)
    (out / SIDEBAR).write_text(json.dumps(sidebar(guide), indent=2), encoding=ENCODING)
    return len(chapters) + 1


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', required=True, help='the staging folder, built afresh')
    arguments = parser.parse_args(argv)
    count = stage(out=arguments.out)
    print(MSG_STAGED.format(count=count, folder=arguments.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
