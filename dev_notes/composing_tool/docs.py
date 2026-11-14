# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import pathlib, textwrap
ROOT = pathlib.Path('/Users/michaeldehaan/Devel/llamatron')
NEW_PAGES = {'Rock': 'ROCK.md', 'Soundtrack': 'SOUNDTRACK.md', 'TV theme': 'TV_THEME.md', 'Video game': 'VIDEO_GAME.md'}
INTRO = "# {title}\n\nThe demo songs in the {style} style. Each is described below, with the features it uses; [Demo Songs](../DEMOS.md) lists every demo.\n"
SECTIONS = [
    ('POP.md', 'rick_rolling', 'Dance-Pop', "A late-eighties dance-pop song in the manner of Never Gonna Give You Up, with a melody of its own: an octave-bouncing synth bass, off-beat chord stabs and a disco beat. The bass and the stabs are one bar each, moved through the chords by Progression chains."),
    ('POP.md', 'peanut_buttercup', 'Soul-Pop', "A late-sixties soul-pop song in the manner of Build Me Up Buttercup, with a melody of its own: a bouncing piano, horn stabs on the off-beats and a tambourine on two and four, the harmony moved by Progression chains."),
    ('POP.md', 'bless_the_rains', 'Soft-Rock', "An early-eighties soft-rock song in the manner of Africa, with a melody of its own: a marimba riff in sixteenths, congas, a shaker and a cowbell, and a warm pad, the marimba moved through the chords by Progression."),
    ('POP.md', 'goodnight_world', 'Synth-Pop', "An early-eighties synth-pop song in the manner of Sweet Dreams, with a melody of its own: a sixteenth-note synth bass leaping an octave, a cold string pad, a drum machine and a saw lead."),
    ('ROCK.md', 'spot_over_there', 'Power-Pop', "An early-2000s power-pop song in the manner of Stacy's Mom, with a melody of its own: driving eighth-note power chords, a pick bass and a crash on every chorus bar."),
    ('ROCK.md', 'know_your_slang', 'Indie Rock', "An indie rock song in two moods after the Shins' New Slang and Know Your Onion, with melodies of its own: a strummed acoustic guitar with a tambourine, then a jangling electric guitar and a full kit. The acoustic guitar's track strums down and up."),
    ('ROCK.md', 'green_men', 'Pop-Punk Strumming', "A pop-punk song in the manner of Green Day and Sum 41 at 180 beats a minute. The guitar track strums every power chord down, tight, as a pick rakes the strings, and in the bridge a Strum generator in the clips' chains wins over the track's strum and rakes down and up, looser."),
    ('ROCK.md', 'training_montage', 'Arena-Rock', "An early-eighties film anthem in the manner of Eye of the Tiger, for a training montage: muted guitar chords hit in a syncopated rhythm with the kick, then a driving rock beat and a brass lead. The rhythm and the melody are its own."),
    ('ROCK.md', 'aliens_counting', 'Synth-Rock', "A mid-eighties synth-rock anthem in the manner of The Final Countdown, with a fanfare of its own in sixteenths on synth brass, over power chords, a pad and a rock beat with crashes."),
    ('ROCK.md', 'not_werewolves', 'Outlaw Piano Ballad', "A piano ballad in the manner of Warren Zevon's Frank and Jesse James, opening with a stride piano scene at a tempo of its own, 150 beats a minute, before the ballad settles at 80 with a fiddle singing the tune."),
    ('ROCK.md', 'annandale', 'Jazz-Rock', "A seventies jazz-rock song in the manner of Steely Dan's My Old School, lightly swung: an electric piano on the scale chord 7, so that the Progression gives each chord the seventh its scale says, and a horn line answered two scale steps below by a transposed second horn track."),
    ('ROCK.md', 'volcano', 'Guitar Showpiece', "A solo guitar showpiece in the manner of Van Halen's Eruption: the band hits a chord and leaves the guitar alone for runs in thirty-second notes, a trill, and tapped arpeggios, a held chord broken up by an arpeggiator in sixteenth-note triplets."),
    ('FOLK.md', 'secret_chord', 'Hallelujah Chords', "Leonard Cohen's chords for Hallelujah in 6/8, played by a piano, a bass and strings through Progression chains, under a cello melody of its own. The scale's own chord on 3, E minor, stands where the song has E major."),
    ('TV_THEME.md', 'sax_reindeer', 'Novelty Saxophone Romp', "A breakneck romp in the manner of Yakety Sax: a tenor saxophone running in sixteenths over a honky-tonk piano, an oom-pah bass and a two-beat kit, with every run its own."),
    ('TV_THEME.md', 'spy_hunting', 'Spy Theme', "A late-fifties spy theme in the manner of Peter Gunn: a low guitar riff doubled by the bass, a surf beat, brass stabs and a tenor saxophone, every scene one chorus of a minor twelve-bar blues from a Progression. The riff and the tune are its own."),
    ('TV_THEME.md', 'phoenix_foundation', 'Action-Show Theme', "A mid-eighties action-show theme in the manner of MacGyver, with a melody of its own on synth brass, over rock guitar, a pulsing synth bass and keys broken into sixteenths over two octaves by an arpeggiator."),
    ('TV_THEME.md', 'uphill_cops', 'Voice-Led Piano Theme', "A gentle theme in the manner of Hill Street Blues, with a melody of its own on solo piano. The chords come from a Progression and then a Voice leading generator, which voices each chord nearest the one before, so that the chords glide."),
    ('TV_THEME.md', 'forgot_your_name', 'Sitcom Theme', "A warm sitcom theme in the manner of Cheers, with a melody of its own on clarinet, over a piano comping on the beats, a bass and soft drums."),
    ('TV_THEME.md', 'tropical_51', 'Big-Band Police Theme', "A big-band theme in the manner of Hawaii Five-0, with a fanfare of its own: pounding toms, timpani, strings racing in sixteenths, a brass section and trombones answering."),
    ('TV_THEME.md', 'not_painless', 'Wistful Guitar Theme', "A gentle theme in the manner of M*A*S*H, with a melody of its own on flute: a nylon guitar picks its chords through an arpeggiator, round the circle of fifths in minor."),
    ('TV_THEME.md', 'mysterious_spooky', 'Creepy Harpsichord Theme', "A playful theme in the manner of The Addams Family, with a tune of its own: a harpsichord creeping up in half steps, finger snaps on two and four, a tuba bass and a church organ."),
    ('SOUNDTRACK.md', 'get_the_traps_egon', 'Spooky Funk Film Theme', "A mid-eighties funk-pop film theme in the manner of Ghostbusters, in G mixolydian, with a two-bar synth bass riff, stabs and a brass hook of its own, and a sci-fi wail for the ghosts."),
    ('SOUNDTRACK.md', 'angry_shark', 'Shark Score', "An orchestral score in the manner of Jaws: two low notes a half step apart, slow at first and faster as the danger comes, the scenes ramping the tempo from 70 to 140 beats a minute and back, with a horn call of its own."),
    ('SOUNDTRACK.md', 'very_large_mammals', 'Boogie-Woogie Film Tune', "A boogie-woogie tune in the manner of Baby Elephant Walk, shuffled by a factory groove: a walking boogie bass through the twelve-bar blues, an organ, horn stabs on a dominant seventh and a calliope with a tune of its own."),
    ('SOUNDTRACK.md', 'four_wheels_g', 'Eighties Synth Film Theme', "A mid-eighties synth theme in the manner of Axel F, with a hook of its own: a staccato saw lead leaping octaves, a bouncing octave bass in sixteenths, chord stabs and bells."),
    ('ELECTRONIC.md', 'sandworm', 'Trance Builds by Density', "A late-nineties trance anthem in the manner of Sandstorm, with a stuttering sixteenth-note lead of its own. Each build is a scene whose Density rises from 25% to 100%, thinning every clip to its strongest beats and filling it back in."),
    ('ELECTRONIC.md', 'microwave_snacks', 'Synthesizer Novelty Tune', "An early-seventies novelty tune in the manner of Popcorn, with a tune of its own that bounces off a high repeated note every other sixteenth, and claves kept to 5 of every 8 steps by their track's Euclidean mask."),
    ('ELECTRONIC.md', 'nomore_nomore', 'Eurodance', "An early-nineties eurodance song in the manner of What Is Love, with a melody of its own: an off-beat synth bass, a syncopated piano, a pad and sixteenth hats."),
    ('SOUNDTRACK.md', 'strange_woodworking', 'Analog-Synth Score', "A dark synth score in the manner of Survive and John Carpenter: a held chord broken into a pulsing sixteenth-note sequence by an arpeggiator, a deep bass, a halo pad and a slow square lead, with a hat kept to a Euclidean rhythm by its track."),
    ('VIDEO_GAME.md', 'fang_removal', 'Gothic Stage Theme', "A gothic eight-bit stage theme in the manner of Castlevania's Vampire Killer, in D harmonic minor, whose major fifth chord gives the style its pull: a square-wave lead, a second square two scale steps below and a driving octave bass. The melody is its own."),
    ('VIDEO_GAME.md', 'incoming_message', 'Ten Stages', "Nine minutes after Mega Man 2's intro and boss themes: ten stages, each in a key of its own set by its scenes, changing theme exactly nine times with a one-bar fill between each, the last a reprise of the first. Each stage's patterns are named after it, stage_0 to stage_9, and a chip track breaks its chords into thirty-second notes as the old sound chips did."),
]
for name, title in (('ROCK.md', ('Rock', 'rock')), ('SOUNDTRACK.md', ('Soundtrack', 'soundtrack')), ('TV_THEME.md', ('TV Theme', 'TV theme')), ('VIDEO_GAME.md', ('Video Game', 'video game'))):
    path = ROOT / 'docs' / 'demos' / name
    if not path.exists():
        path.write_text(INTRO.format(title=title[0], style=title[1]))
for page, stem, heading, text in SECTIONS:
    path = ROOT / 'docs' / 'demos' / page
    body = path.read_text()
    if f'`{stem}.yml`' in body:
        continue
    wrapped = textwrap.fill(text, width=100)
    body = body.rstrip('\n') + f"\n\n## {heading}: `{stem}.yml`\n\n{wrapped}\n\n<!-- generated by internal_tools/demo_summary.py: about {stem} -->\n<!-- end of the generated summary of {stem} -->\n"
    path.write_text(body)
print(len(SECTIONS))
