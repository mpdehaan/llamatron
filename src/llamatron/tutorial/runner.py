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

"""The runner of a video tutorial: presses the plan's keys into the running tracker, one every pace, and keeps what the plan says.

A key is pressed the way the tests press one, straight into the screen that is open, and then the
event loop is given its turn, so that the next step reads the screen as it is after the key. The
pace is the seconds between two keys, a human's when a video is made and nothing when the suite
runs the tutorial, and a sentence said is given longer, so that a viewer can take it in. What is
said and called out is kept with the second it was said at, and shown in the caption strip at the foot
of the screen (tui/caption_strip.py), which the tutorial gives the app, a part at a time when it's too
long for one line, each part given time to read in proportion to its length.
"""

import asyncio
import time

from textual.pilot import Pilot

from llamatron.strings.narration import MSG_TUTORIAL_KEYS, MSG_TUTORIAL_LEFT_OUT, MSG_TUTORIAL_SAID
from llamatron.tui.key_table import key_event
from llamatron.tui.caption_strip import CaptionStrip, parts
from llamatron.tutorial.plan import TutorialPlan
from llamatron.tui.drawing import NOTHING
from llamatron.tutorial.steps import Gap, Press, Say, Wait

# The seconds between two keys when a video is made, how many of those a sentence is given, and the share of them a key typed into a dialog waits, the user's choice of 2026-11-10: typing into a dialog goes twice as fast.
HUMAN_PACE = 0.35
SAY_PAUSES = 6
DIALOG_TYPING_SHARE = 0.5
NO_PACE = 0.0
# The extra seconds after every caption, so that it can be read, the user's choice of 2026-11-10; nothing when the tutorial runs at no pace.
LINE_SECONDS = 1.0
# How fast a viewer reads a caption, in characters a second, which gives a long caption longer than a short one.
READING_CHARACTERS_PER_SECOND = 15
# How often a Wait asks again whether what it waits for has come.
WAIT_CHECK_SECONDS = 0.05


class Narrator:
    """Keeps each sentence the tutorial says and each key it calls out, with the second it was said at."""

    __slots__ = ('said',)

    def __init__(self):
        self.said = []

    def say(self, *, text, seconds):
        """Keep a sentence, or what a key is called as it is pressed."""
        self.said.append((seconds, text))

    def parts(self, text):
        """Return what is shown of a sentence, one part after another: the sentence whole, for a narrator that shows nothing."""
        return [text]

    def show(self, part):
        """Show one part of what is said, which only a narrator that shows captions does."""

    def gap(self):
        """Set what follows apart, which only a narrator that shows captions does."""


class CaptionNarrator(Narrator):
    """Shows what is said in the caption strip at the foot of every page, a part at a time when it's too long for one line, as well as keeping it."""

    __slots__ = ('app', 'strip')

    def __init__(self, *, app, strip):
        super().__init__()
        self.app = app
        self.strip = strip

    def parts(self, text):
        return parts(text=text, width=self.app.size.width)

    def show(self, part):
        self.strip.show(part)
        self.app.redraw_pages()

    def gap(self):
        self.show(NOTHING)


class TutorialRunner:
    """Runs a plan's steps in the tracker as a background task, and reports what happened."""

    __slots__ = ('app', 'plan', 'pace', 'narrator', 'now', 'pressed', 'finished', 'problem', 'started_at', 'ended_at', '_task')

    def __init__(self, *, app, plan, pace=HUMAN_PACE, narrator=None, now=time.monotonic):
        self.app = app
        self.plan = plan
        self.pace = pace
        self.narrator = Narrator() if narrator is None else narrator
        self.now = now
        self.pressed = 0
        self.finished = False
        # What stopped the plan, or None.
        self.problem = None
        self.started_at = None
        self.ended_at = None
        self._task = None

    def start(self, *, then=None):
        """Begin pressing keys on the tracker's event loop, and call then once the plan has run, or failed."""
        self.started_at = self.now()
        self._task = asyncio.ensure_future(self._run(then))
        return self._task

    async def _run(self, then):
        pilot = Pilot(self.app)
        try:
            for step in self.plan.steps():
                if isinstance(step, Press):
                    if step.called is not None:
                        await self._caption(pilot=pilot, text=step.called, least=NO_PACE)
                    self.app.screen.on_key(key_event(step.key))
                    self.pressed += 1
                    await self._pause(pilot=pilot, seconds=self.key_seconds(step))
                elif isinstance(step, Say):
                    await self._caption(pilot=pilot, text=step.text, least=self.pace * SAY_PAUSES)
                elif isinstance(step, Gap):
                    self.narrator.gap()
                elif isinstance(step, Wait):
                    while not step.until():
                        await asyncio.sleep(WAIT_CHECK_SECONDS)
                        await pilot.pause()
                    await self._pause(pilot=pilot, seconds=step.seconds if self.pace > NO_PACE else NO_PACE)
        except Exception as error:
            self.problem = error
        self.ended_at = self.now()
        self.finished = True
        if then is not None:
            then()

    async def _caption(self, *, pilot, text, least):
        """Keep what is said and show it a part at a time, each part for at least least seconds, or as long as it takes to read, and a second more; nothing waits at no pace."""
        self.narrator.say(text=text, seconds=self.now() - self.started_at)
        for part in self.narrator.parts(text):
            self.narrator.show(part)
            await self._pause(pilot=pilot, seconds=self.caption_seconds(part=part, least=least))

    def caption_seconds(self, *, part, least):
        """Return how long a caption shows: long enough to read and a second more, or nothing at no pace."""
        if self.pace <= NO_PACE:
            return NO_PACE
        return max(least, len(part) / READING_CHARACTERS_PER_SECOND) + LINE_SECONDS

    def key_seconds(self, press):
        """Return how long to wait after a key: the pace, or a share of it for a key typed into a dialog."""
        return self.pace * DIALOG_TYPING_SHARE if press.in_dialog else self.pace

    async def _pause(self, *, pilot, seconds):
        """Let the tracker handle the key, then wait the pace. At no pace, as the tests run it, the tracker only handles what the key sent, with no
        wait for the computer to go idle, which took a fiftieth of a second a key or far more on a busy machine (the user's idea of 2026-11-11)."""
        if self.pace > NO_PACE:
            await pilot.pause()
            await asyncio.sleep(seconds)
        else:
            await pilot.pause(NO_PACE)

    def report(self):
        """Return the lines of what the tutorial said and left out, and how many keys it pressed, for after the tracker has closed."""
        lines = [MSG_TUTORIAL_SAID.format(seconds=seconds, text=text) for seconds, text in self.narrator.said]
        lines += [MSG_TUTORIAL_LEFT_OUT.format(what=what) for what in self.plan.left_out]
        if self.ended_at is not None:
            lines.append(MSG_TUTORIAL_KEYS.format(count=self.pressed, seconds=self.ended_at - self.started_at))
        return lines


def tutorial(*, target, port=None, pace=HUMAN_PACE):
    """Return what a Launch's driven_by takes: a function of the app that builds the plan of the target set and the runner that presses its keys, playing at the end through the MIDI port, or not with none, and shows the caption strip at the foot of the tracker's pages."""
    def driving(app):
        strip = CaptionStrip()
        app.show_caption_strip(strip)
        return TutorialRunner(app=app, plan=TutorialPlan(app=app, target=target, driver=port), pace=pace, narrator=CaptionNarrator(app=app, strip=strip))
    return driving
