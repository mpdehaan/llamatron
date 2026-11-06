# llamatron: a Python language and framework for producing MIDI clips.
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

"""Installs llamatron, including the Live set that the renderer builds from.

    pip install .

This adds the llamatron command, which turns a song file into a Live set or MIDI files.
"""

import re
from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).resolve().parent
# The version is read from the code's own version.py, as text, so that installing doesn't run it.
VERSION_FILE = HERE / 'src' / 'llamatron' / 'version.py'
VERSION_LINE = re.compile(r"^VERSION = '([^']+)'$", re.MULTILINE)
VERSION = VERSION_LINE.search(VERSION_FILE.read_text(encoding='utf-8')).group(1)

setup(
    name='llamatron',
    version=VERSION,
    description='A tracker for writing MIDI clips and Ableton Live sets',
    long_description=(HERE / 'README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    author='Michael DeHaan',
    license='GPL-3.0-or-later',
    python_requires='>=3.15',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    package_data={'llamatron': ['templates/*.als']},
    install_requires=(HERE / 'requirements.txt').read_text(encoding='utf-8').split(),
    entry_points={'console_scripts': ['llamatron = llamatron.cli:main']},
    # The template is read from a real file next to the code.
    zip_safe=False,
)
