# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""User strings: every piece of text llamatron shows people, one module for each way the text is used.

errors.py holds what went wrong (ERR_), help.py each page's help (HELP_), and the rest hold the
MSG_ constants: labels.py the names of things on screen, legends.py what keys are called and do,
messages.py what the tracker says, marks.py what it draws, about.py the About dialog, cli.py the
command line and names.py the names the program gives to things. Nothing here does anything, and
no other package defines a constant with one of the three prefixes, so that all the wording can
be read and edited in one place.
"""
