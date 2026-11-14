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
"""The About dialog's text: the cow, the version line, the links, the quotes and the license.

Each constant starts with MSG_.
"""

# tui/screens/page.py and tui/key_table.py: the key names, the labels and the words every page shares
# Shown at the bottom right of the main screen.
MSG_SITE = 'home.laserllama.net'

# AboutDialog: the cowsay cow saying the program's name, then the version, the links, a quote and the license.
MSG_ABOUT_TITLE = 'About llamatron'
MSG_COW_BUBBLE_TOP = ' {rule}'
MSG_COW_BUBBLE_TEXT = '< {text} >'
MSG_COW_BUBBLE_BOTTOM = ' {rule}'
MSG_COW = (
    '        \\   ^__^',
    '         \\  (oo)\\_______',
    '            (__)\\       )\\/\\',
    '                ||----w |',
    '                ||     ||',
)
MSG_ABOUT_VERSION = 'version {version}, built {date} ({time})'

# tui/components/title_card.py: the title on black, in block letters, with the scanner and the address under it, which the start screen, the
# recordings' splash and the batch videos show, and the start screen's prompt; and the READY box of the batch videos. Each block letter is
# five rows of five columns, drawn twice as wide where the screen has room.
MSG_SPLASH_WORD = 'LLAMATRON'
MSG_SPLASH_ADDRESS = 'github.com/mpdehaan/llamatron.git'
MSG_START_PROMPT = 'Press ENTER to Start'
MSG_READY_WORD = 'READY'
MSG_BLOCK = '█'
MSG_BLOCK_LETTERS = {
    'A': (' ███ ', '█   █', '█████', '█   █', '█   █'),
    'D': ('████ ', '█   █', '█   █', '█   █', '████ '),
    'E': ('█████', '█    ', '████ ', '█    ', '█████'),
    'L': ('█    ', '█    ', '█    ', '█    ', '█████'),
    'M': ('█   █', '██ ██', '█ █ █', '█   █', '█   █'),
    'N': ('█   █', '██  █', '█ █ █', '█  ██', '█   █'),
    'O': (' ███ ', '█   █', '█   █', '█   █', ' ███ '),
    'R': ('████ ', '█   █', '████ ', '█  █ ', '█   █'),
    'T': ('█████', '  █  ', '  █  ', '  █  ', '  █  '),
    'Y': ('█   █', ' █ █ ', '  █  ', '  █  ', '  █  '),
}
MSG_ABOUT_WEB = 'web: https://github.com/mpdehaan/llamatron.git'
MSG_ABOUT_BLOG = 'blog: https://laserllama.substack.com'
MSG_ABOUT_MORE = 'more: https://{site}'
MSG_ABOUT_POWERED = 'powered by CowAmp technology'
MSG_ABOUT_QUOTES = (
    'moo',
    'gee brain, what are we doing tomorrow night',
    'better music through chaos',
    'beep beep, bleep bloop beep',
    'inconceivable!',
    'narf!',
    "where we are going we don't need roads",
    'zoom factor 5, enhance',
    'warning: sporks are incompatible',
    'dynotherms connected',
    'infracells up',
    'megathrusters are go',
    'by the power of grayskull?',
    'zug zug',
    'more work?',
    'reticulating splines..',
    'meep meep',
    'decepticons, transform!',
    'this is the way',
    'there is no spoon',
    'give me sight beyond sight',
    "right now, it's happening",
    'I suggest a new strategy, R2',
    'Danger! Danger, Will Robinson!',
    'The Claw! The Claw!',
    'Banana?',
    'Get Equipped With: Item-2!',
    'Allons-y!',
    'Geronimo!',
    "Don't blink.",
    'Two to beam up',
    'Indeed.',
    "Sir, I've been thinking...",
    'we do what we must, because we can',
    'this was a triumph',
    "I'm making a note here, huge success",
    'these points of data make a beautiful line',
    'it is dangerous to go alone, take this!',
    'warp zone, please choose a pipe',
    "we don't need no thought control",
    "whoa, we're halfway there",
    'once upon a time, not so long ago',
    'As you wish.',
    'what is the average velocity of an unladen swallow?',
    'Wi n0t trei a hpliday in Sweden this yer?',
    'We are the Knights Who Say... Ni!',
    'all your base are belong to us',
)
MSG_EIGHT_BALL = 'the magic eight ball says: {answer}'
MSG_EIGHT_BALL_ANSWERS = (
    'it is certain', 'it is decidedly so', 'without a doubt', 'yes definitely', 'you may rely on it',
    'as I see it, yes', 'most likely', 'outlook good', 'yes', 'signs point to yes',
    'reply hazy, try again', 'ask again later', 'better not tell you now', 'cannot predict now', 'concentrate and ask again',
    'do not count on it', 'my reply is no', 'my sources say no', 'outlook not so good', 'very doubtful',
)
MSG_ABOUT_LICENSE = 'License: GPLv3'
MSG_ABOUT_COPYRIGHT = 'copyright: Michael DeHaan {year}'
