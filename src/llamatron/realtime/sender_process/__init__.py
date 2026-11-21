# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The sender process's part of real-time playback: the engines that send each event at its moment, the outputs they send
through, timestamped by CoreMIDI or sent at once by python-rtmidi, and the process that holds them apart from the tracker."""
