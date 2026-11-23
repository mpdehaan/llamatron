# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What several screens share: the scale and root pickers, the note lengths, the file suffixes and the key lists that list pages build from."""
from llamatron.engine.generators.arp import model as arp_model
from llamatron.user_strings import errors, messages


SONG_SUFFIX = '.yml'
SONG_SUFFIXES = (SONG_SUFFIX, '.yaml')
# The MIDI files the import's picker shows.
MIDI_SUFFIXES = ('.mid', '.midi')
ORDERS = list(arp_model.ORDERS)
DEFAULT_ORDER = ORDERS[0]


def list_keys(*, page, extra, always=()):
    """Return the keys every list of named things has: + adds, the extra ones only with something selected, and the always ones whatever is."""
    result = [page.bind(page.KEYS.BACK, action=page.go_back), *page.move_keys(), page.bind(page.KEYS.ADD, action=page.add)]
    if page.current() is not None:
        result += extra
    result += always
    return result


def move_key(page):
    """Return M, which picks up the selected row for Move mode."""
    return page.bind(page.KEYS.MOVE, action=page.start_moving)


def play_through(*, page, play, what, said):
    """Start real-time playback through the page's transport: tell why nothing can play if so, and otherwise play and say on the status line what started, or that what (the scene or clip, named) starts at the next bar."""
    problem = page.app.transport.problem()
    if problem is not None:
        page.tell(problem.title, *problem.lines)
        return
    tried = page.app.transport.try_play(play)
    if tried.refusal is not None:
        page.tell(errors.ERR_CANT_PLAY_TITLE, tried.refusal)
        return
    page.say(messages.MSG_STARTS_AT_NEXT_BAR.format(what=what) if tried.answer else said)
