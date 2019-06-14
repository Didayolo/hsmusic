# Huge Symbolic Music Dataset (HSMusic)

import midi
import numpy
import os
import unicodedata
import re

lowerBound = 24
upperBound = 102
DATA_DIR = 'data'
OUTPUT_DIR = 'output'

def str_to_tag(string):
    """ Convert a character string into another one in a standard format for naming.
        Converts to lowercase, removes non-alpha characters, and converts spaces to hyphens.
        Example: 'La Marseillaise' -> 'la_marseillaise'.
    """
    string = str(string)
    string = unicodedata.normalize('NFKD', string) #.encode('ascii', 'ignore').decode('ascii')
    string = re.sub('[^\w\s-]', '', string).strip().lower()
    string = re.sub('[-\s]+', '_', string)
    return string
    
def to_tags(midifile):
    """ Read metadata from a MIDI file and return a list of tags.
    """
    pattern = midi.read_midifile(midifile)
    print(pattern[0])

def to_matrix(midifile):
    """ Read a MIDI file and convert it into a binary matrix.
    """
    pattern = midi.read_midifile(midifile)
    timeleft = [track[0].tick for track in pattern]
    posns = [0 for track in pattern]
    statematrix = []
    span = upperBound-lowerBound
    time = 0
    state = [[0,0] for x in range(span)]
    statematrix.append(state)
    while True:
        if time % (pattern.resolution / 4) == (pattern.resolution / 8):
            # Crossed a note boundary. Create a new state, defaulting to holding notes
            oldstate = state
            state = [[oldstate[x][0],0] for x in range(span)]
            statematrix.append(state)
        for i in range(len(timeleft)):
            while timeleft[i] == 0:
                track = pattern[i]
                pos = posns[i]
                evt = track[pos]
                if isinstance(evt, midi.NoteEvent):
                    if (evt.pitch < lowerBound) or (evt.pitch >= upperBound):
                        pass
                        # print "Note {} at time {} out of bounds (ignoring)".format(evt.pitch, time)
                    else:
                        if isinstance(evt, midi.NoteOffEvent) or evt.velocity == 0:
                            state[evt.pitch-lowerBound] = [0, 0]
                        else:
                            state[evt.pitch-lowerBound] = [1, 1]
                elif isinstance(evt, midi.TimeSignatureEvent):
                    if evt.numerator not in (2, 4):
                        # We don't want to worry about non-4 time signatures. Bail early!
                        # print "Found time signature event {}. Bailing!".format(evt)
                        return statematrix
                try:
                    timeleft[i] = track[pos + 1].tick
                    posns[i] += 1
                except IndexError:
                    timeleft[i] = None
            if timeleft[i] is not None:
                timeleft[i] -= 1
        if all(t is None for t in timeleft):
            break
        time += 1
    return statematrix

def to_midi(statematrix, name="example"):
    """ Write a binary matrix as a MIDI file under the filename name+'.mid'.
    """
    statematrix = numpy.asarray(statematrix)
    pattern = midi.Pattern()
    track = midi.Track()
    pattern.append(track)
    span = upperBound-lowerBound
    tickscale = 55
    lastcmdtime = 0
    prevstate = [[0,0] for x in range(span)]
    for time, state in enumerate(statematrix + [prevstate[:]]):  
        offNotes = []
        onNotes = []
        for i in range(span):
            n = state[i]
            p = prevstate[i]
            if p[0] == 1:
                if n[0] == 0:
                    offNotes.append(i)
                elif n[1] == 1:
                    offNotes.append(i)
                    onNotes.append(i)
            elif n[0] == 1:
                onNotes.append(i)
        for note in offNotes:
            track.append(midi.NoteOffEvent(tick=(time-lastcmdtime)*tickscale, pitch=note+lowerBound))
            lastcmdtime = time
        for note in onNotes:
            track.append(midi.NoteOnEvent(tick=(time-lastcmdtime)*tickscale, velocity=40, pitch=note+lowerBound))
            lastcmdtime = time
        prevstate = state
    eot = midi.EndOfTrackEvent(tick=1)
    track.append(eot)
    midi.write_midifile(os.path.join(OUTPUT_DIR, '{}.mid'.format(name)), pattern)
    
if __name__ == "__main__":
    print('Huge Symbolic Data (HSMusic) version 0.0')
    # TODO: Cool ASCII art
    midiname = os.path.join(DATA_DIR, 'test.mid')
    print(str_to_tag('Str to tag TEST /!/'))
    print(to_tags(midiname))
