# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The four parts of a Timing generator, each a row of steps with an amount of its own, and the names a file gives each part's
settings: rush_steps, rush_step, rush_amount and the like."""

RUSH = 'rush'
DRAG = 'drag'
SHORTEN = 'shorten'
GLIDE = 'glide'
# In the order its page shows them: the two that move notes in time, then the two that change their length.
PARTS = (RUSH, DRAG, SHORTEN, GLIDE)
# The parts that move notes early or late, after every chain has run, rather than change them.
MOVING_PARTS = (RUSH, DRAG)

STEPS = 'steps'
STEP = 'step'
AMOUNT = 'amount'


def steps_of(part):
    """Return the file's name for a part's row of steps, such as rush_steps."""
    return part + '_' + STEPS


def step_of(part):
    """Return the file's name for how long each of a part's steps is, such as rush_step."""
    return part + '_' + STEP


def amount_of(part):
    """Return the file's name for a part's amount, such as rush_amount."""
    return part + '_' + AMOUNT
