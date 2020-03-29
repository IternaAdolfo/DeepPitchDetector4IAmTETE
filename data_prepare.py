#!/usr/bin/env python3

import os
import re
import tempfile
import math
import random
import numpy as np
from midiutil.MidiFile import MIDIFile

#https://0xfe.blogspot.com/2020/02/pitch-detection-with-convolutional.html

GM_PATCHES = [
    0,  # Acoustic Grand Piano
    3,  # Honky-tonk Piano
    6,  # Harpsichord
    11,  # Vibraphone
    16,  # Drawbar Organ
    19,  # Church Organ
    22,  # Harmonica
    24,  # Acoustic Guitar (nylon)
    26,  # Electric Guitar (jazz)
    30,  # Distortion Guitar
    32,  # Acoustic Bass
    33,  # Electric Bass (finger)
    40,  # Violin,
    42,  # Cello
    48,  # String Ensemble 1
    51,  # SynthStrings 2
    52,  # Choir Aahs
    56,  # Trumpet
    57,  # Trombone
    61,  # Brass Section
    65,  # Alto Sax
    66,  # Tenor Sax
    71,  # Clarinet
    73,  # Flute
    78  # Whistle
]


class Note:
    values = {
        "c": 0,
        "d": 2,
        "e": 4,
        "f": 5,
        "g": 7,
        "a": 9,
        "b": 11
    }

    names = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]

    # Takes a note in the form "C#4", "Bb2", "A5", etc. and returns
    # the MIDI note number.
    @classmethod
    def note(cls, str):
        matches = re.match('^([ABCDEFGabcdefg])([b#s]?)([0-9])$', str)

        note = matches.group(1).lower()
        acc = matches.group(2).lower()
        octave = int(matches.group(3))

        shift = 0
        if acc == "b":
            shift -= 1
        elif acc == '#':
            shift += 1
        elif acc == 's':
            shift += 1

        value = ((octave + 1) * 12) + cls.values[note] + shift
        return int(value)

    @classmethod
    def notes(cls, note_list):
        return map(cls.note, note_list)


class Sample:
    SOUNDFONT = "soundfont.sf2"

    @staticmethod
    def note_to_freq(note, octave, a_440=440.0):
        note_map = {}
        for i, note_name in enumerate(Note.names):
            note_map[note_name] = i

        key = note_map[note] + ((octave - 1) * 12) + 1
        return a_440 * pow(2, (key - 46) / 12.0)

    def __init__(self, name, program=0, key='A', octave=4, volume=100, tempo=60):
        self.name = name
        self.mid_filename = name + '.mid'
        self.tmp_filename = self.name + "-" + "full" + ".wav"

        self.key = key
        self.octave = octave
        self.note = str(key) + str(octave)
        self.freq = Sample.note_to_freq(key, octave)

        self.file = MIDIFile(1, adjust_origin=True)
        self.file.addTempo(0, 0, tempo)
        self.file.addProgramChange(0, 0, 0, program)
        self.file.addNote(0, 0, Note.note(self.note), 0, 1, volume)

    def save(self):
        with open(self.mid_filename, "wb") as out:
            self.file.writeFile(out)

    def make_wav(self):
        self.save()
        os.system("fluidsynth -l -i -a file %s %s -F %s -r 44100" %
                  (Sample.SOUNDFONT, self.mid_filename, self.tmp_filename))

    def transform_wav(self, suffix, start_s=0, duration=1, pitch_shift_hz=0, resample_hz=44100, resample_bits=16):
        shift_cents = 0
        if pitch_shift_hz != 0:
            shift_cents = 1200.0 * \
                          math.log((self.freq + pitch_shift_hz) / self.freq, 2)

        self.new_freq = self.freq + pitch_shift_hz

        wav_file = self.name + "-" + \
                   "%.3f" % (self.new_freq) + "-" + "S" + \
                   str(pitch_shift_hz) + "-" + suffix + ".wav"
        print("Writing ", wav_file, "with sample rate",
              resample_hz, "and bit depth", resample_bits, ("(shift %s)" % shift_cents))

        os.system("sox -t raw -r 44100 -e signed -b 16 -c 2 %s -r %s -b %s %s norm -0.1 pitch %s remix 2 trim %f %f" %
                  (self.tmp_filename, resample_hz, resample_bits, wav_file, shift_cents, start_s, duration))

    def clean(self):
        # Keep only transformed
        #os.remove(self.mid_filename)  # Remove midi file
        #os.remove(self.tmp_filename)  # Remove -full .wav file
        print(".")


def main():
    for octave in range(4, 5):
        random.shuffle(GM_PATCHES)
        for patch in range(0, 15):
            program = GM_PATCHES[patch]
            for key in Note.names:
                sample = Sample("data/note-%s%s-P%s" % (key, octave, program),
                                program=program, key=key, octave=octave)
                sample.make_wav()
                for pitch_shift_hz in np.concatenate((np.array([0]), np.random.randint(10, 80, 5))):
                    sample.transform_wav(
                        "attack", duration=0.33, pitch_shift_hz=pitch_shift_hz)
                    sample.transform_wav(
                        "sustain", start_s=0.33, duration=0.33, pitch_shift_hz=pitch_shift_hz)
                    sample.transform_wav(
                        "decay", start_s=0.66, duration=0.33, pitch_shift_hz=pitch_shift_hz)

                sample.clean()


if __name__ == "__main__":
    main()
