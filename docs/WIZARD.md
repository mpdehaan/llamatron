# Song Wizard

The song wizard makes a whole song from a few choices: a genre, a band, chords, tunes and a form. A songwriter starts the same way, deciding what kind of song it is, who plays, what the chords are and which section follows which, before anyone plays a note. The wizard asks for those decisions and writes the patterns, tracks, scenes and clips that a band of that genre would play, and the result is an ordinary song of the set, every note of which can be edited afterwards on Arrange and in the pattern editor.

`F5` opens the wizard from any page. Nothing in the set changes until Apply, and undo then takes the whole song away again. Each run makes a different song from the same choices.

The wizard is in progress: its panels change from one version to the next, and this page shows what each panel holds now. How to work through a song with the wizard will get a page of its own.

## Wizard Layout

The tree at the left lists the wizard's panels, and the settings of the panel under the cursor show at the right. Up and Down move through the tree, Left and Right close and open a panel that has panels under it, `ENTER` or Tab moves into the settings, and `ESC` or Tab moves back to the tree. `L` (listen) plays what the panel under the cursor would make, a tune, a hook, a player or a section, through FluidSynth. `ESC` in the tree closes the wizard, and asks first.

## Genre

The Genre panel comes first, since every other panel starts from what the genre usually does. Choosing a genre and, under Genre in the tree, a subgenre fills in the key, the scale, the tempo, the meter, the band and the form with what that kind of song usually has. Each can then be changed, and the panel shows how long the song will play.

Another genre brings another band and another form, so choosing one after settings were changed by hand first asks, in a Change Genre question that counts what would be lost, such as band settings and new takes of tunes, and what is kept: a tune whose notes were edited stays as written through any change of genre.

![The song wizard's Genre panel](screenshots/wizard_genre.svg)

## Band

The Band panel chooses who is in the band. Each player is switched in or out, Sounds chooses the band's set of instrument sounds, Guitarists chooses one guitar or two, Tune played by names the player who carries the tune, and Answered by names the player who answers the tune in the gaps between its lines.

![The song wizard's Band panel](screenshots/wizard_band.svg)

## Players

Each player in the band has a panel under Band in the tree. Plays chooses the kind of part the player plays, such as a chiming arpeggio or strummed chords, and Sound the instrument. Comes in and Lays out say when the player joins the song and when the player rests, as a real player waits for the second verse or drops out before a chorus. Reacts and Dynamics set how much the player follows the rest of the band and the song's louds and softs, and the gauges below them set how busy and how varied the part is.

![The panel of one player, the rhythm guitar](screenshots/wizard_player.svg)

## Composition

Composition holds the panels of what the song is made of: its chords, its melody style, its tunes and its hook.

### Chords

The Chords panel chooses the chord progression: one of the genre's progressions by name, or any, which leaves the choice to the wizard when the song is made.

![The song wizard's Chords panel](screenshots/wizard_chords.svg)

### Melody

The Melody panel chooses the style the tunes are written in, such as a walk by steps or a tune of leaps, and how the tune is phrased: how long its lines are, how long the breath after a line is, and how often a line starts early.

![The song wizard's Melody panel](screenshots/wizard_melody.svg)

### Tunes

The Tunes panel has a heading for each kind of section that has a tune, one for the verses and one for the choruses, so that every verse plays the same tune as verses do. `Space` or `ENTER` on a heading opens the heading, which holds the Tune of that kind of section and its Played by field. Tune played by chooses the player who carries the tune through the song, a singer, a lead guitar or any player of the band but the bass and the drums, and the Played by field of a kind of section goes by the song until another player is chosen there, or nobody, for a section with no tune. The player given the tune plays it in place of that player's usual part. `ENTER` (edit notes) on a tune opens the tune in the pattern editor, where the notes are edited as any pattern's are, and `ESC` there comes back to the wizard. A tune that was edited is marked `(edited)`, belongs to the person from then on, and is never written over by another choice; `Bksp` gives the tune back to the wizard. `T` (new take) writes another tune for that kind of section alone, leaving the rest of the song as it was, and the row then says which take it shows.

![The song wizard's Tunes panel](screenshots/wizard_tunes.svg)

### Hooks

The Hooks panel switches the song's hook on, the short phrase a listener goes away humming, and shows the hook's notes. Its sections choose the hook's kind, where in the song the hook is said, and the riff, a short figure a player repeats under the song. New hook draws another.

![The song wizard's Hooks panel](screenshots/wizard_hooks.svg)

## Form

The Form panel chooses the sections the song plays and in what order. Song plan gives every section a place in a rise and fall across the whole song, Contrast sets how far the loud sections stand from the quiet ones, and Starts with and Ends with choose how the song begins and ends. The list at the bottom says what the plan gives each section.

![The song wizard's Form panel](screenshots/wizard_form.svg)

## Sections

Each section has a panel under Form in the tree. On a section, `I` (insert) adds a section before it, `A` (add) adds one at the end, `C` (copy) copies it, `Bksp` (delete) removes it and `M` (move) carries it to another place. The section's settings choose its kind, how many bars it lasts and its energy, and its headings open the section's tune, harmony, shape, the way it joins the section after it, and who plays in it.

![The panel of one section, the first verse](screenshots/wizard_section.svg)

## Apply

The Apply panel sums the song up, its genre, key, tempo, form and length, and `ENTER` on the Apply button makes the song and shows it on [Arrange](ARRANGE.md).

![The song wizard's Apply panel](screenshots/wizard_apply.svg)
