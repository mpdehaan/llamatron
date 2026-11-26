# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The corpus as Python objects for meta-analysis (111 A): every dataset fetched into output/library/ read into one kind of piece, each
piece's measures cached as tables in output/library/tables/, and analyses that do arithmetic on those tables. Development only, never
imported by llamatron itself, which needs no downloaded data. Every piece keeps its source, and every source its terms and how
far its data can be trusted, so that a source can be measured on its own before it is pooled with others, and so that knowledge
calibrated from it carries its license (.claude/GENRES.md, "Licenses Travel With Knowledge")."""
