# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How a percentage of what it scales is shown, as a velocity's or a tempo's is: "125%", and "100%" for a blank one."""

from llamatron.user_strings import marks

# What a percentage left blank scales by: nothing changes.
UNCHANGED = 100


def percent_shown(percent):
    """Return a percentage as a field shows it, one that isn't whole, as an import may write, to two places."""
    if percent == int(percent):
        return marks.MSG_PERCENT_SHOWN.format(percent=int(percent))
    return marks.MSG_PART_PERCENT_SHOWN.format(percent=float(percent))
