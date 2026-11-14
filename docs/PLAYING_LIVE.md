# Playing Live

A song can be played in real time while you work on it, and edited while it plays. This page covers playing from Arrange; [Instruments](INSTRUMENTS.md) covers setting up the sound, and [MIDI Setup](MIDI_SETUP.md) covers connecting a Mac to a synthesizer or Ableton Live and testing the connection.

## Real-Time Playback

Playing in real time is for composing: you hear the song through your synthesizers or FluidSynth as you work, and nothing about playing changes an export. To set it up, add an instrument on the Instruments page, `I` on the main screen, choosing one of this computer's MIDI output ports and a channel, or FluidSynth, and choose that instrument in each track's editor. Adding the first instrument turns the main screen's Real Time switch on, and `T` on the main screen turns it on and off.

While the switch is on, Arrange has its play controls: a `▶ song` button in the corner over the scene names, which the arrows reach; a `▶` beside each clip, in place of the left end of the clip's bar; and `Space` wherever the cursor is.

## Playing and Stopping

- **`Space` on the corner** plays the song from the top, and **`Space` on a scene's name** plays the song from that scene. Either way, every clip of the scene starts together. When the scene is done, each clip passes a start to the clip below it as its Advance says, as [Clips](CLIPS.md#advance) describes, and a scene with Launch together on starts as a whole when a start reaches any of its clips, stopping whatever the scene above still plays, loops included. With the defaults, the song plays from there to the end exactly as Live's Arrangement View plays the export. A scene whose every clip loops can't play, just as it can't export, since such a scene would wait forever.
- **`Space` on a clip** plays that clip on its own, whatever its scene says, replacing whatever its track was playing, while the other tracks go on. `Space` on a playing clip stops its track.
- **Every start by hand waits for the next bar** while anything plays, as Live's default quantization does. The bars are counted in the song's time signature from the start of the earliest clip playing, the music goes on until then, and the status line says, for example, `scene 2 starts at the next bar`. A scene or clip shorter than a bar hands over at its end, and with nothing playing, a start happens at once.
- **`Space` again** on the corner or on a playing scene stops everything, as `Ctrl+T` does on any page. The song keeps playing when you leave Arrange or open another page, so that you can edit it as it plays; only a listening page's preview stops when you leave that page. Stopping, like quitting, sends note offs for what was sounding, then all notes off and all sound off on each channel.
- **A track with no instrument** is silent in real time but still counts in the arrangement, so the song keeps its shape. If an instrument's device isn't connected, a dialog says which one, and nothing plays until another device is chosen on the Instruments page.

## Playback Lights

While something plays, Arrange shows what is playing:

- the corner reads `■ song`;
- a playing clip's `▶` becomes a red `■`, and its repeat mark counts down the repeats left;
- a green `●` follows a track's name while a note sounds on the track;
- the playing scene's bar fills from the left as the song moves through the scene, and each playing clip's bar fills the same way through the clip's repeats, a looping clip's bar filling once per play of its scene and starting over;
- the clock at the right of the crumbs reads, for example, `▶ 0:22 / 3:00`.

These are llamatron's only colours, and the shapes change too, so the state shows without the colours.

## Live Editing

An edit made while something plays is heard on what plays, from the moment the song's Live response setting says: the next bar by default, each playing clip's next pass, or at once. Typed digits are heard once you stop typing, a song with no seed keeps its random choices for the whole play, and a scene whose every clip you make loop plays on until you launch another. While the song plays, a track or scene with clips can't be deleted, though anything can be inserted. None of this affects an export, which plays every scene once through.
