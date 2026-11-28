# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A sample of Python for the tests of the check of named values: each line the check must report ends with the
comment `flagged`, and every other line must pass. It breaks the rule on purpose, so it lives beside the tests."""

PREVIEW_CHANNEL = 15
NAMED = (
    ("black", 0),
    ("red", 7),
)


def sample(settings, values):
    tempo = settings["tempo"]  # flagged
    run(values, 48000)  # flagged
    first = values[0] + 1
    shown_rows = 7
    resonance, drive = 0.3, 0.5
    print("the A gauge moves Slow")  # 48 kHz
