# Developer Guide

How llamatron's code is put together, and how to change it: building and
running it, where each part lives, and the usual changes, a page and a field
above all. [Testing](TESTING.md) says how the checks work, and
[Architecture](ARCHITECTURE.md) is the tour of the parts for readers
who won't edit them.

## Overview

llamatron is a Rust program, one Cargo workspace in `src/`, a crate a layer.
Each crate uses only the crates below it, and the compiler holds it to that,
since a crate can reach only what its manifest names:

- `math`: exact numbers for lengths and times, and the random sources.
- `strings`: every word the program shows, in `src/strings/src/texts/`.
- `model`: the set as its file holds it: values, objects, the schema that
  says what a file may hold, and reading and writing the file.
- `engine`: a song played into clips, with its generators and timing.
- `exporters` and `importers`: MIDI files and Live sets out, MIDI files in.
- `backend`: the sound and the timing of real-time playback: the built-in
  synths, FluidSynth and the MIDI sender, on threads of their own.
- `tracker`: the text UI, its pages, dialogs and keys, the document the pages
  edit, and real-time playback's transport and player.
- `compare`: the development tool `llamatron-compare`, which holds llamatron
  to the program it replaced, walks llamatron's pages, takes the screenshots
  and writes the key map.

A song travels up the layers: the model reads the file into objects, the
engine plays a song into a grid of clips, and the exporters write the grid,
or the tracker's player sends it as it plays.

## Building and Running

```
sh setup.sh                                   # once: the tools' environment, then the build
sh build.sh                                   # build llamatron after a change or a git pull
./llamatron.sh examples/learning/08_tie.yml   # the tracker on a set
./llamatron.sh SET --to midi                  # export without the tracker
```

`build.sh` builds the release program, `src/target/release/llamatron`. For
quick work, `cargo build` and `cargo test` in `src/` work as in any Rust
project.

## Where Things Live

| To change | Look in |
| --- | --- |
| What a set file may hold, a setting's range or default | `src/model/src/schema/` |
| How a set is read, written or migrated from an older layout | `src/model/src/file/` |
| The objects: the set, songs, tracks, scenes, clips, patterns | `src/model/src/objects/` |
| How a song plays into notes | `src/engine/src/realizer.rs`, `src/engine/src/clip_player.rs`, `src/engine/src/pattern_player.rs` |
| A generator | `src/engine/src/generators/` |
| An export | `src/exporters/src/` |
| A page or a dialog | `src/tracker/src/screens/`, in folders by what the page edits |
| A key | `src/tracker/src/generated/keybindings.rs` |
| A word the program shows | `src/strings/src/texts/` |
| Real-time playback | `src/tracker/src/realtime/` and `src/backend/` |

## How a Page Works

Every screen is a page: a type that implements the `Page` trait
(`src/tracker/src/page.rs`). The tracker keeps a stack of pages, the main
screen at the bottom; `app.show_page(...)` opens one over the rest and
`app.go_back()` closes it. Each time a key is pressed the tracker asks the top
page which keys it offers where its cursor is, finds the key among them and
hands it to the page, and then draws the page again. A page never draws
straight to the terminal: it hands back lines of styled text, and the tracker
lays them out under a header and over a legend of the keys it offered.

So a page answers a few questions:

- its name and its crumbs, the path shown at the top left;
- the keys it offers now, which are both what it handles and what its legend
  shows;
- what a key does;
- its lines, for a width and a height;
- what kind of place its cursor is on, such as a clip on Arrange, which lets
  the walk of the program, the key map and the tests tell one place from
  another.

A page changes the set only through the document, `app.document`, so that
every change is checked by the schema and becomes one step of undo.

## Adding a Settings Page

Most pages that edit a thing are settings pages: a column of fields, perhaps
tabs, and buttons. A settings page is written as a form, which says what it
shows and what each edit stores, and `FieldPage`
(`src/tracker/src/screens/field_page.rs`) does the rest: drawing, moving the
cursor, the keys every field shares, typing, picking and clearing. The Scale
page is a small example to read first
(`src/tracker/src/screens/set/scale_page.rs`). A new settings page needs:

1. A type holding what the page edits, such as the scale's name, which
   implements `Form`: its name, its key class, its crumbs, its theme, its form
   and `apply`.
2. Its fields, which `form` returns as nodes in order. Each field is made by
   one of `Field`'s constructors in `src/tracker/src/forms/nodes.rs`, by the
   kind of value it holds: `Field::number` for a number in a range,
   `Field::choice` for one of a list, `Field::toggle` for on and off,
   `Field::text` for typed text, `Field::name` for the thing's name,
   `Field::button` for an action, and `Field::custom` for a field whose keys
   the page handles itself. A tab box is a `Node::TabBox` of tabs, each a list
   of columns of fields.
3. What each edit stores: `apply(app, id, edit)` receives the field's id and
   the edit, such as `Edit::Number(7)` or `Edit::Clear`, and changes the set
   through `app.document.change_set`.
4. Its keys, as a class of its own in `src/tracker/src/generated/keybindings.rs`
   that takes the settings page's shared bindings and adds its own.
5. Its words, as constants in `src/strings/src/texts/`.
6. A way in: the page or key that opens it calls
   `app.show_page(Box::new(FieldPage::new(...)))`.

## Adding a Field

A field added to a settings page is three small changes:

1. A setting for it in the schema, with its range and default, where it
   stores something new in the file. `src/model/src/schema/` holds every
   setting, and the setting's one check is what both reading a file and the
   field's edits ask.
2. The field in the page's `form`, made with the constructor of its kind, its
   label a constant in `src/strings/src/texts/labels.rs`, and its id a named
   constant of the page.
3. Its edit in the page's `apply`: the new value stored through the document.

The label width, the cursor, the legend, `[` and `]`, ENTER, `Bksp` and undo
then all work as on every other field.

## Keys and Words

Every key binding is in one table, `src/tracker/src/generated/keybindings.rs`:
a module for each page, dialog and component, each binding the keys that press
it, the name the legend shows and what it does, and lists saying which
bindings the legend and the help show. A page offers only its own class's
bindings. After changing a key, `internal_tools/key_map.sh` writes
`.claude/reference/KEYMAP.md` again.

Every text the program shows is a constant in `src/strings/src/texts/`, by how
it is used: `errors.rs` for what went wrong, `labels.rs` for names on screen,
`legends.rs` for keys, and `messages.rs` for the status line and dialogs. A text with blanks is filled by name with `named`, so
that `"no pattern called ({name})"` reads the same in the code and on screen.

## Rules of the Code

The code is meant to be read by people who maintain it without help:
readable over clever, a function short enough to read at a glance, every
function with a comment saying what it does, no `unwrap` outside tests, and a
named constant for every number or text whose purpose isn't plain. The rules
in full are in `.claude/rules/STYLE.md` and `.claude/rules/RUST.md`, and
`.claude/rules/UX.md` says how every page and dialog behaves.
