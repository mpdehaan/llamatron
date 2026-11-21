# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Engine's questions about the generator plugins found: each one's controller, and which methods of the controller's a
plugin fills in, worked out once, so that the Realizer calls a method only where it does something."""

import functools

from llamatron.engine.generators.controller import GeneratorController
from llamatron.model.schema import generator_plugins


def controller_of(name):
    """Return the controller of the generator plugin of a name."""
    return generator_plugins.plugins()[name].controller


@functools.cache
def fills(*, name, method):
    """Return whether the controller of the generator plugin of a name fills in one of the controller's methods."""
    return getattr(type(controller_of(name)), method) is not getattr(GeneratorController, method)


@functools.cache
def moves_pitches(name):
    """Return whether the generators of the plugin of a name move a clip's pitches, which a drum pattern is spared."""
    return controller_of(name).MOVES_PITCHES


@functools.cache
def follows_tracks(name):
    """Return whether the generators of the plugin of a name play from what the tracks their settings name play."""
    return controller_of(name).FOLLOWS_TRACKS


@functools.cache
def shape_of(name):
    """Return the shape the generators of the plugin of a name lay over a finished clip, or None."""
    return controller_of(name).SHAPE
