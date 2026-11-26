# Compliance

The rules for licences, credits, names and git history, every one the user's. They come before the other rules where
they meet.

## Licence

- Every commit MUST be strictly compliant with GPLv3, the licence of llamatron, full text in `LICENSE`: only code and work
  under a licence compatible with GPLv3 enter the repository. Code that is not open source is never consulted, and code
  examples are sought among GPLv3-compatible projects.
- Every Rust, Python and shell file, new and empty ones included, MUST start with the three-line header copied from any
  source file (`llamatron: a music program`, the copyright line, `SPDX-License-Identifier: GPL-3.0-or-later`), as `//`
  comments in Rust and `#` comments elsewhere, above the module's documentation and below a `#!` line.
- Where an open emulator or synthesizer already models a sound (a chip's tables, a circuit's measured behaviour) under a
  licence compatible with GPLv3, the built-in synths use its work rather than a model of our own, and credit its authors
  and project in the code that holds it and in `docs/CREDITS.md`. The credit, with the work's licence, is a comment
  directly above each algorithm taken from it, besides the module's header; the implementation may be our own, read from
  theirs.
- `docs/CREDITS.md` MUST be kept current: every open-source project whose code or work is used is listed there with its
  authors and licence, in the same change that uses it.

## Names, Trademarks and Brands

- No file MUST hold a copyrighted term, a trademark or brand information, such as a product's or a manufacturer's name,
  unless the user waives it for an explicit reference. The waivers:
  - a file format llamatron writes or reads, named even after a product, such as "Ableton Live set" and `--to ableton`;
  - llamatron's inspirations, Ableton's Session View, the Elektron Monomachine and the Sequentix Cirklon, in `README.md`,
    the introduction of `docs/GUIDE.md`, `docs/WHY_LLAMATRON.md` and `CLAUDE.md`;
  - a program people open llamatron's files in, named where the documents say which programs read an export, such as
    GarageBand;
  - open-source projects, named freely, and credited when their code is used;
  - the General MIDI standard's own names for its sounds.
- Where a waived trademark is named, its notice stands in `docs/CREDITS.md`, as the Monomachine's and the Cirklon's do.
- No text the program shows or raises, its help included, names a manufacturer or a product beyond the waivers; an
  instrument, an engine or an effect is named and described by what it does.
- Synth and effect designs name no product or maker. Every engine, effect and modulator draws on synthesis ideas that
  many people developed over decades, so each is described by what it does and how it sounds. A design is never held to a
  past instrument, nor made to copy one's design or sound; new ideas are the aim.

## Git History

- History is rewritten only on the user's word, with a full mirror saved to `~/Devel/backup_llamatron/` first.
- A request to edit git history, for any reason, is never recorded in the queue, the ideas files or the designs, nor is its
  reason.
