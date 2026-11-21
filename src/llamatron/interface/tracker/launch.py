# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""How the tracker was launched: the command line's flags for playing a set on its own, which the demo recorder passes too.

--autoplay opens on Arrange and plays the song from the top, as Space on the corner does.
--autoplay-quit-when-finished does that and quits once the song has ended. --visualizer does it with
a visualizer mode over the clip area in place of the clips, the one way Arrange opens on one. --launch-for-recording
opens on the splash first, shows it again once the song has ended, leaves the save mark off the
header, and refuses a song that would wait on a looping clip forever, since a recording of it would never end (internal_tools/record_demo.py).
An interactive launch for recording, opens Arrange after the splash with the cursor on the corner and
plays nothing: the person recording starts it with Space, performs, and ends the take by stopping from the corner, or
with Esc, after which the splash shows again and the tracker quits. A
launch driven from outside, which internal_tools/make_video_tutorial.py makes, hands the app to something
that presses keys into it, the video tutorial (interface/tutorial/runner.py), which the tracker knows nothing of.
"""

from llamatron.interface.tracker import batch_stage
from llamatron.interface.tracker.components.title_card import whole_title_seconds
from llamatron.interface.tracker.uses import looping_scenes
from llamatron.model.file.checks import listed
from llamatron.user_strings import errors

# How long the splash shows before Arrange, how long Arrange is shown before play starts, and how long the last note is given to ring out before the tracker quits.
SPLASH_SECONDS = 6.0
LEAD_IN_SECONDS = 1.0
LEAD_OUT_SECONDS = 2.0
# How long the tracker waits after the closing splash before it quits, unless the recorder asks for longer.
NO_HOLD = 0.0
# How often the launch asks whether the song is still playing, once it has started.
FINISHED_CHECK_SECONDS = 0.25


class Launch:
    """What the tracker does on its own once it opens, by the command line's flags."""

    __slots__ = (
        'autoplay', 'quit_when_finished', 'for_recording', 'test_splash', 'max_seconds', 'splash_seconds', 'lead_in_seconds', 'lead_out_seconds',
        'driven_by', 'visualizer', 'hold_seconds', 'interactive', 'batch_video', 'opening_only', 'ready_seconds', 'title_seconds', 'alternate', 'scroll_text', 'scroll_seconds', 'announce', 'details',
    )

    def __init__(self, *, autoplay=False, quit_when_finished=False, for_recording=False, test_splash=False, max_seconds=None,
                 splash_seconds=SPLASH_SECONDS, lead_in_seconds=LEAD_IN_SECONDS, lead_out_seconds=LEAD_OUT_SECONDS,
                 driven_by=None, visualizer=None, hold_seconds=NO_HOLD, interactive=False, batch_video=False, opening_only=False,
                 ready_seconds=batch_stage.READY_SECONDS, title_seconds=None, alternate=True, scroll_text=None, scroll_seconds=None, announce=False, details=False):
        """quit_when_finished implies autoplay, and so does visualizer, which opens Arrange with that mode showing; test_splash shows the start screen for splash_seconds, fading out, and quits (internal_tools/demo_splash_screen.py), and max_seconds quits after that many seconds whatever plays. The three timings are for the tests, which can't wait.

        driven_by is a function of the app that returns what drives the tracker from outside, the
        video tutorial (tutorial.runner.tutorial), whose start(then=) is called once the tracker
        is open; with it, quit_when_finished quits once whatever it played has ended.

        Launched for recording, a song that ends shows the splash again for splash_seconds after the
        lead-out, and the tracker then waits hold_seconds more
        before it quits, so that the recorder can end the video while the splash still shows.

        batch_video, records a batch video (interface/tracker/batch_stage.py): the title on black for
        its whole length, then Arrange with the READY box for ready_seconds, then the song with the
        visualizer mode filling the scene frame, and black at the end, with no splash; it implies
        for_recording and quit_when_finished. opening_only stops it where the song would start, cutting
        to black and quitting, to look at the opening alone (internal_tools/demo_splash_screen.py).
        alternate, on unless switched off, alternates the frame between the clips and the visualizer.

        interactive, launched for recording, plays nothing by itself: Arrange waits on its corner for
        the person recording, and the take ends when they stop everything from the corner or press Esc.

        announce, shows each scene's name as it starts, where a visualizer mode's name
        shows, and no mode's name then. details, opens Arrange with its details view showing,
        as D shows it, wherever the clips show.
        """
        self.autoplay = (autoplay or quit_when_finished or visualizer is not None) and driven_by is None
        self.quit_when_finished = quit_when_finished
        self.for_recording = for_recording
        self.test_splash = test_splash
        self.max_seconds = max_seconds
        self.splash_seconds = splash_seconds
        self.lead_in_seconds = lead_in_seconds
        self.lead_out_seconds = lead_out_seconds
        self.driven_by = driven_by
        # The visualizer mode Arrange opens with over the clips, by its name on the command line, or None for the clips.
        self.visualizer = visualizer
        self.hold_seconds = hold_seconds
        self.interactive = interactive and for_recording
        self.batch_video = batch_video
        self.opening_only = opening_only and batch_video
        self.ready_seconds = ready_seconds
        # Whether a batch video's frame alternates between the clips and the visualizer, the default.
        self.alternate = alternate
        # The words that cross the screen after the opening title, the demo's name when an example is recorded, or None for none.
        self.scroll_text = scroll_text
        # Whether each scene's name is shown as the scene starts, in place of the visualizer modes' names.
        self.announce = announce
        # Whether Arrange starts with its details view open, for a recording of the clips with their details.
        self.details = details
        # How long the words are shown: as long as they take to cross the screen, None, unless a test says less.
        self.scroll_seconds = scroll_seconds
        # How long a batch video's title shows: the whole of it unless a test says less.
        self.title_seconds = whole_title_seconds() if title_seconds is None else title_seconds
        if batch_video:
            self.for_recording = True
            self.quit_when_finished = not self.opening_only
            self.autoplay = False

    def is_plain(self):
        """Return whether the tracker opens as it always has, on the main screen, doing nothing by itself."""
        return not (self.autoplay or self.for_recording or self.test_splash or self.max_seconds is not None or self.driven_by is not None)

    def needs_set(self):
        """Return whether the launch needs a set to play: everything but the splash alone."""
        return not self.is_plain() and not self.test_splash


    def boxes_playing_scene(self):
        """Return whether Arrange draws a blue box around the playing scene and no box around its cursor: in a recording nobody performs."""
        return self.for_recording and not self.interactive


def recording_problem(song):
    """Return why a song can't be launched for recording, or None: a scene whose every clip loops waits there for the human, so the recording would never end."""
    scenes = looping_scenes(song)
    if scenes:
        return errors.ERR_RECORDING_SONG_LOOPS.format(scenes=listed(scenes))
    return None
