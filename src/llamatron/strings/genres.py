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

"""The genre library's words: the names the corpus's pieces are labelled with, every measure's name in plain words, and what
the analyzer says was doubtful in a file, kept here apart from the code, the user's choice.

Each constant starts with MSG_; the classes group the names, which are shown as they are.
"""


class StyleName:
    """The names the corpus's pieces are labelled with, by the development tools that measure them."""

    NEW_ORLEANS = 'New Orleans jazz'
    SWING = 'swing'
    BEBOP = 'bebop'
    COOL_JAZZ = 'cool jazz'
    MODAL_JAZZ = 'modal jazz'
    HARD_BOP = 'hard bop'
    JAZZ_FUSION = 'jazz fusion'
    BAROQUE = 'baroque'
    CLASSICAL_ERA = 'classical era'
    ROMANTIC = 'romantic'
    IMPRESSIONISM = 'impressionism'
    RAGTIME = 'ragtime'
    MARCH = 'march'
    FOLK = 'folk'
    CELTIC = 'Celtic'
    JS_BACH = 'J. S. Bach'
    HANDEL = 'Handel'
    VIVALDI = 'Vivaldi'
    TELEMANN = 'Telemann'
    MODERNISM = 'modernism'
    CHINESE_FOLK = 'Chinese folk song'
    HAYDN = 'Haydn'
    MOZART = 'Mozart'
    CHOPIN = 'Chopin'


# Every measure's name in plain words, by its holder and field (genres/measures/registry.py).
MSG_MEASURE_LABELS = {
    'tempo.low': 'tempo',
    'meter.usual': 'time signature',
    'meter.others': 'other time signatures',
    'meter.changes': 'changes of time signature',
    'harmony.progressions': 'chord progressions',
    'harmony.qualities': 'chord qualities',
    'harmony.modes': 'modes',
    'harmony.beats_per_chord': 'beats a chord',
    'harmony.chromatic': 'notes outside the key',
    'harmony.rich': 'chords of four notes or more',
    'harmony.planing': 'chords moved in parallel',
    'harmony.whole_tone': 'time in a whole-tone scale',
    'bass.bar_span': 'left hand reach in a bar',
    'texture.chordal': 'chords struck at once',
    'modulation.travel': 'fifths between its keys',
    'bass.reach': 'bass range',
    'texture.span': 'range of all its notes',
    'harmony.borrowed': 'borrowed chords',
    'modulation.often': 'how often the key changes',
    'modulation.moves': 'key changes, in half steps',
    'modulation.where': 'where the key changes',
    'modulation.reached': 'how a new key is reached',
    'drums.grooves': 'drum grooves',
    'drums.fills': 'drum fills',
    'drums.fill_kinds': 'kinds of drum fill',
    'drums.timekeeper': 'timekeeping voice',
    'groove.swing': 'swing',
    'groove.push': 'playing ahead of or behind the beat',
    'groove.ghosts': 'ghost notes',
    'groove.feel': 'feel',
    'groove.feel_changes': 'changes of feel',
    'bass.motion': 'bass motion',
    'bass.notes_per_bar': 'bass notes a bar',
    'melody.steps': 'moves by step',
    'melody.reversals': 'leaps that turn back',
    'melody.range': 'range in half steps',
    'melody.phrase_bars': 'phrase length in bars',
    'melody.arches': 'phrases that arch',
    'melody.peak': 'where a phrase peaks',
    'melody.repetition': 'repetition of figures',
    'melody.density': 'notes a beat',
    'expectation.surprise': 'surprise',
    'expectation.contrast': 'contrast of surprise',
    'expectation.uncertainty': 'uncertainty',
    'expectation.familiarity': 'familiarity',
    'phrasing.space': 'space between phrases',
    'phrasing.burstiness': 'flurries against held notes',
    'phrasing.rhythmic_variety': 'rhythmic variety',
    'phrasing.dynamics': 'range of loudness in the lead',
    'phrasing.looseness': 'looseness against the grid',
    'phrasing.arc': 'phrases that build and release',
    'hook.strength': 'hook strength',
    'hook.hummable': 'hummable',
    'hook.placement': 'hook on the high points',
    'voice_leading.contrary': 'contrary motion',
    'voice_leading.oblique': 'oblique motion',
    'voice_leading.parallels': 'parallel fifths and octaves in a hundred motions',
    'voice_leading.independence': 'independence of the parts',
    'vocal.singable': 'singability of the lead',
    'vocal.range': 'sung range in half steps',
    'vocal.syllabic': 'notes that each carry a syllable',
    'vocal.breath_bars': 'bars sung on a breath',
    'vocal.carriers': 'sounds that carry the sung line',
    'texture.parts': 'parts sounding',
    'texture.call_and_response': 'call and response',
    'texture.density': 'notes a beat in every part together',
    'sounds.roles': 'sounds of each role',
    'energy.arc': 'energy over the song',
    'energy.contrast': 'contrast of energy',
    'solos.presence': 'songs with a solo',
    'solos.count': 'solos in a song',
    'solos.bars': 'bars in a solo',
    'solos.players': 'who solos',
    'solos.spots': 'where solos come',
    'solos.bases': 'what solos are played over',
    'solos.improvised': 'how improvised solos are',
    'solos.trading': 'soloists trading turns',
    'spacing.bass_to_lead': 'half steps from the bass to the lead',
    'spacing.crowding': 'parts crowding one register',
    'spacing.mud': 'muddy low register, share of beats',
    'spacing.hollow': 'hollow spacing, share of beats',
    'spacing.masking': 'lead masked, share of notes',
}


# genres/hearing/cleaning.py and genres/hearing/midi_file.py: what was doubtful about the parts of a song that came from a MIDI file.
MSG_DOUBT_DUPLICATES = '{count} notes written twice were counted once'
MSG_DOUBT_STUCK = '{count} notes left sounding for many bars were cut short'
MSG_DOUBT_JUNK = 'tracks of a few notes were left out, as credits or tests ({count})'
MSG_DOUBT_EFFECTS = 'sound effects were left out ({names})'
MSG_DOUBT_PERCUSSION = 'percussion on ordinary channels was read as drums ({names})'
MSG_DOUBT_ONE_DRUM = 'the drums play one drum only, so the kit is probably mapped wrongly and the drum reading is unsure'
MSG_DOUBT_NO_KICK = 'the drums have no kick drum, so the kit may be mapped unusually and the drum reading is unsure'
MSG_DOUBT_TEMPOS = 'the tempo changes during the song ({count} changes); the tempo given is the one held longest'
MSG_DOUBT_METERS = 'the time signature changes ({meters}); the measures count in the one held longest'


# genres/hearing/cleaning.py: how a list of names is joined.
MSG_GENRE_LIST_JOIN = ', '


class GrooveName:
    """The name of every drum groove."""

    ROCK_BEAT = 'rock beat'
    ROCK_AND_OF_THREE = 'rock beat, kick on the and of three'
    ROCK_SYNCOPATED = 'syncopated rock beat'
    ROCK_SIXTEENTHS = 'rock beat on sixteenth hats'
    ROCK_QUARTER_HATS = 'rock beat on quarter hats'
    ROCK_RIDE = 'rock beat on the ride'
    ROCK_FOUR_FLOOR = 'four-on-the-floor rock'
    ROCK_HALF_TIME = 'half-time rock'
    ROCK_DRIVING_EIGHTHS = 'driving eighth kicks'
    ROCK_TOM_GROOVE = 'tom groove'
    MOTORIK = 'motorik'
    PUNK_DRIVE = 'punk drive'
    SKANK_BEAT = 'skank beat'
    D_BEAT = 'd-beat'
    ROCK_SHUFFLE = 'rock shuffle'
    HALF_TIME_SHUFFLE = 'half-time shuffle'
    TRIPLET_KICK_GROOVE = 'triplet kick groove'
    TWELVE_EIGHT = '12/8 groove'
    BO_DIDDLEY = 'Bo Diddley beat'
    GALLOP = 'gallop'
    DOUBLE_KICK = 'double kick'
    THRASH_BEAT = 'thrash beat'
    BLAST_BEAT = 'blast beat'
    DOOM_DIRGE = 'doom dirge'
    GROOVE_METAL_CHUG = 'groove metal chug'
    TRAIN_BEAT = 'train beat'
    TWO_BEAT = 'two-beat'
    COUNTRY_TWO_STEP = 'country two-step'
    BLUEGRASS_CHOP = 'bluegrass chop'
    WALTZ = 'waltz'
    SIX_EIGHT = '6/8 ballad'
    MARCH = 'march'
    SHUFFLE = 'shuffle'
    SLOW_BLUES = 'slow blues'
    SWING_RIDE = 'swing ride'
    BRUSH_BALLAD = 'brush ballad'
    BEBOP_RIDE = 'bebop ride and comping'
    DIXIELAND_TWO = 'Dixieland two-beat'
    SECOND_LINE = 'second line'
    JAZZ_WALTZ = 'jazz waltz'
    BIG_BAND_SHOUT = 'big band shout'
    SPY_GROOVE = 'spy groove'
    MOTOWN = 'Motown beat'
    NORTHERN_STOMP = 'northern soul stomp'
    FUNK_GHOSTS = 'funk with ghost notes'
    LINEAR_FUNK = 'linear funk'
    NEW_ORLEANS_FUNK = 'New Orleans funk'
    DISCO = 'disco'
    GOSPEL_SHUFFLE = 'gospel shuffle'
    NEW_JACK_SWING = 'new jack swing'
    AFROBEAT = 'Afrobeat'
    BOSSA_NOVA = 'bossa nova'
    SAMBA = 'samba'
    SON_CLAVE = 'son clave groove'
    RUMBA_CLAVE = 'rumba clave groove'
    SONGO = 'songo'
    MOZAMBIQUE = 'mozambique'
    TUMBAO_ROCK = 'Latin rock'
    ONE_DROP = 'one drop'
    ROCKERS = 'rockers'
    STEPPERS = 'steppers'
    HOUSE = 'house'
    TECHNO = 'techno'
    MINIMAL_TECHNO = 'minimal techno'
    TRANCE = 'trance'
    BIG_ROOM = 'big room'
    EURODANCE = 'eurodance'
    ELECTRO = 'electro'
    BREAKBEAT = 'breakbeat'
    BIG_BEAT = 'big beat'
    DRUM_AND_BASS = 'drum and bass two-step'
    JUNGLE = 'jungle'
    UK_GARAGE = 'UK garage'
    IDM_BROKEN = 'broken IDM beat'
    GLITCH_STUTTER = 'glitch stutter'
    SYNTH_POP = 'synth-pop'
    GATED_POP = 'gated eighties pop'
    DANCE_POP = 'dance-pop'
    SYNTHWAVE = 'synthwave'
    DARK_PULSE = 'dark pulse'
    CHIPTUNE = 'chiptune'
    BOOM_BAP = 'boom bap'
    TRAP = 'trap'
    LO_FI = 'lo-fi'
    TIMPANI_ROLL = 'timpani roll'
    MARCHING_SNARE = 'marching snare'
    NO_DRUMS = 'no drums'
