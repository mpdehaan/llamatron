# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Lets `python -m llamatron` work the same as the llamatron command."""

import sys

from llamatron.cli import main

sys.exit(main())
