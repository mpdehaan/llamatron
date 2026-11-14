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

import importlib, sys
sys.path.insert(0, '/Users/michaeldehaan/Devel/llamatron/test')
from lib import write
from rendering import render_file
from llamatron.exporters.timing import timed_events
from llamatron.tui.document import Document
for module in sys.argv[1:]:
    for make in importlib.import_module(module).SONGS:
        path, seconds = write(make())
        real = float(Document.load(path).lengths().song_seconds())
        flag = '' if abs(real - 180) <= 8 or 'incoming' in path else '  <-- LENGTH'
        grid = render_file(path)
        low, high, notes, lengths = 999, 0, 0, ''
        for scene in grid.get_rows():
            clips = [(c.get_name(), grid.get_clip(row=scene, column=c)) for c in grid.get_columns() if grid.get_clip(row=scene, column=c)]
            if len({clip.total_length() for _, clip in clips}) != 1:
                lengths += f' [{scene.get_name()}: uneven]'
            for name, clip in clips:
                found = [p for _, _, p, _ in timed_events(clip=clip, scale=clip.get_scale())[0]]
                notes += len(found)
                if found and (min(found) < 21 or max(found) > 108):
                    lengths += f' [{scene.get_name()}/{name}: {min(found)}-{max(found)}]'
        print(f'{path.split("examples/")[1]:42} {real:6.1f}s {notes:6} notes{flag}{lengths}')
