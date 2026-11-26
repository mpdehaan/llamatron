# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Listening: how the clip page and the pattern editor play one clip again and again.

A clip is played as its scene would play it, with its chain, its grabs from the scene's grab track,
its scale and its direction, looping until stopped. When the clip's track has no instrument, a
picker asks which of the set's instruments to play through, for this listening alone. The Patterns
page and the pattern editor listen to a pattern through the pattern preview (interface/tracker/pattern_preview.py),
which plays beside the song with one key and asks nothing.
"""

from llamatron.interface.forms.text import sorted_names
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.screens.shared.shared import play_through
from llamatron.user_strings import errors, messages


def listen(*, page, index, track, name):
    """Play one clip of the current song on its own and again and again, asking for an instrument when its track has none."""
    transport = page.app.transport
    preview = page.app.pattern_preview()
    # With the set's Real Time switch off, the clip plays through General MIDI in FluidSynth, where FluidSynth is installed.
    if not page.document().get_setlist().is_real_time() and preview.general_midi_is_installed():
        refusal = transport.try_play(lambda: preview.play_clip_of_song(index=index, track=track)).refusal
        if refusal is not None:
            page.tell(errors.ERR_CANT_PLAY_TITLE, refusal)
            return
        page.say(messages.MSG_LISTENING_GENERAL_MIDI.format(name=name))
        return
    problem = transport.problem(track=track)
    if problem is not None:
        page.tell(problem.title, *problem.lines)
        return
    setlist = page.document().get_setlist()
    instrument = page.document().song().get_track(track).get_instrument_name()
    said = messages.MSG_LISTENING.format(name=name, track=track)
    what = messages.MSG_CLIP_ON_TRACK.format(name=name, track=track)
    if instrument and setlist.get_instrument(instrument).has_device():
        play_through(page=page, play=lambda: transport.play_clip(index=index, track=track, forever=True), what=what, said=said)
        return
    choices = sorted_names(setlist.get_instrument_names())

    def chosen(place):
        play_through(page=page, play=lambda: transport.play_clip(index=index, track=track, instead={track: choices[place]}, forever=True), what=what, said=said)
    page.ask(dialog=ChoiceDialog(title=messages.MSG_LISTEN_INSTRUMENT_TITLE, options=choices), then=chosen)


def stop_listening(page):
    page.app.pattern_preview().stop()
    page.app.transport.stop_all()
    page.say(messages.MSG_STOPPED)


def listen_to_pattern(*, page, pattern):
    """Play a pattern at once, again and again, beside whatever the song plays (interface/tracker/pattern_preview.py), and say the scale it plays in."""
    preview = page.app.pattern_preview()
    refusal = preview.refusal(pattern)
    if refusal is not None:
        page.refuse(refusal)
        return
    # A song with so many tracks through FluidSynth that one of them has the preview's channel is stopped first, so that the preview's sound never
    # changes a track that plays; the song sends each track's sound again when it next plays.
    if preview.shares_a_channel_with(pattern=pattern, routes=page.app.transport.routes()) and page.app.transport.is_playing():
        page.app.transport.stop_all()
    refusal = page.app.transport.try_play(lambda: preview.play(pattern)).refusal
    if refusal is not None:
        page.tell(errors.ERR_CANT_PLAY_TITLE, refusal)
        return
    scale = preview.scale()
    page.say(messages.MSG_LISTENING_TO_PATTERN.format(name=pattern) if scale is None else messages.MSG_LISTENING_IN_SCALE.format(name=pattern, scale=scale))


def stop_listening_to_pattern(page):
    """Stop the pattern's preview alone, leaving a song played from Arrange playing."""
    page.app.pattern_preview().stop()
    page.say(messages.MSG_STOPPED)


def pattern_listen_keys(*, page, pattern):
    """Return the key that listens to a pattern, or stops it while it is the one playing, and none when nothing could sound: the song names no
    Preview instrument and FluidSynth is not installed."""
    preview = page.app.pattern_preview()
    if pattern is None:
        return []
    if page.document().is_preview(pattern):
        return preview_listen_keys(page=page, instrument=pattern.instrument)
    if preview.playing_pattern() == pattern:
        return [page.bind(page.KEYS.STOP_LISTENING, action=lambda: stop_listening_to_pattern(page))]
    if not preview.can_sound(pattern):
        return []
    return [page.bind(page.KEYS.LISTEN, action=lambda: listen_to_pattern(page=page, pattern=pattern))]


def preview_listen_keys(*, page, instrument):
    """Return the key that listens to an instrument's preview pattern through the instrument, as Listen on its page does, or
    stops it while it plays."""
    preview = page.app.pattern_preview()
    if preview.playing_instrument() == instrument:
        return [page.bind(page.KEYS.STOP_LISTENING, action=lambda: stop_listening_to_pattern(page))]
    return [page.bind(page.KEYS.LISTEN, action=lambda: listen_to_preview(page=page, instrument=instrument))]


def listen_to_preview(*, page, instrument):
    """Play an instrument's preview pattern through the instrument, again and again until stopped."""
    preview = page.app.pattern_preview()
    refusal = preview.instrument_refusal(instrument)
    if refusal is not None:
        page.refuse(refusal)
        return
    trial = page.document().preview_data(instrument)
    refusal = page.app.transport.try_play(lambda: preview.play_instrument(instrument=instrument, trial=trial)).refusal
    if refusal is not None:
        page.tell(errors.ERR_CANT_PLAY_TITLE, refusal)
        return
    page.say(messages.MSG_LISTENING_TO_INSTRUMENT.format(name=instrument))
