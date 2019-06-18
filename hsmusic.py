# Huge Symbolic Music Dataset (HSMusic)
art = """
.##.....##..######..##.....##.##.....##..######..####..######.
.##.....##.##....##.###...###.##.....##.##....##..##..##....##       |~~~~~~~~~~~~~~~|
.##.....##.##.......####.####.##.....##.##........##..##......       |~~~~~~~~~~~~~~~|
.#########..######..##.###.##.##.....##..######...##..##......       |               |
.##.....##.......##.##.....##.##.....##.......##..##..##......   /~~\|           /~~\| 
.##.....##.##....##.##.....##.##.....##.##....##..##..##....##   \__/            \__/
.##.....##..######..##.....##..#######...######..####..######. 
      """
message = 'Huge Symbolic Data (HSMusic) -- version 0.0\n'

import midi
import numpy as np
import pandas as pd
import os
import unicodedata
import re
from shutil import copyfile

lowerBound = 24
upperBound = 102
DATA_DIR = 'data'
OUTPUT_DIR = 'output'
LABELS_FILENAME = 'labels/labels.csv'

def standardize(string):
    """ Convert a character string into another one in a standard format for naming.
        Converts to lowercase, removes non-alpha characters, and converts spaces to hyphens.
        Example: 'La Marseillaise' -> 'la_marseillaise'.
    """
    string = str(string)
    string = unicodedata.normalize('NFKD', string) #.encode('ascii', 'ignore').decode('ascii')
    string = re.sub('[^\w\s-]', '', string).strip().lower()
    string = re.sub('[-\s]+', '_', string)
    return string
    
def to_labels(midifile):
    """ Read metadata from a MIDI file and return a list of labels.
        NOT IMPLEMENTED!
    """
    #pattern = midi.read_midifile(midifile)
    #metadata = pattern[0]
    filename = standardize(os.path.basename(midifile))
    filename = filename.replace('mid', '')
    filename = filename.replace('midi', '')
    labels = filename.split('_')
    return list(set(labels))

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
    return np.asarray(statematrix)

def to_midi(statematrix, name="example", path=''):
    """ Write a binary matrix as a MIDI file under the filename
    """
    statematrix = np.asarray(statematrix)
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
    name = standardize(name)
    midi.write_midifile(os.path.join(path, '{}.mid'.format(name)), pattern)
    
def get_labels():
    """ Read label file and return the labels distribution.
    """
    df = pd.read_csv(LABELS_FILENAME, header=0, index_col=None)
    labels = df['Labels']
    dist = dict()
    for line in labels:
        for label in line.split(';'):
            if label in dist:
                dist[label] += 1
            else:
                dist[label] = 1
    return dist
    
def get_data(labels=None):
    """ Get data associated to specific labels.
        Default behaviour: get the whole dataset.
        Read midi files ...
        If save, create a .npy file with tensors from MIDI folder
    """
    data = []
    files = os.listdir(DATA_DIR)
    files = [x for x in files if '.mid' in x]
    for f in files:
        path = os.path.join(DATA_DIR, f)
        try:
            data.append(to_matrix(path))
        except:
            print('Failed to read {}.'.format(f))
    return np.array(data)

def create_dataset(input_dir, sublabels=None):
    """ Open folder
        Read labels from directory names and filenames
        Copy data to DATA_DIR
        Write labels in labels file
    """
    # create labels file
    if not os.path.isfile(LABELS_FILENAME):
        labels_file = open(os.path.join(LABELS_FILENAME), 'w') # in root dir
        labels_file.write('FileName,Labels\n')
        labels_file.close()
    labels_file = open(os.path.join(LABELS_FILENAME), 'a')
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR) # create data dir
    dirname = os.path.basename(input_dir)
    print(dirname)
    files = os.listdir(input_dir)
    folders = [x for x in files if os.path.isdir(os.path.join(input_dir, x))]
    print(files)
    midifiles = [x for x in files if '.mid' in x]
    labels = to_labels(dirname) # labels of current folder
    if sublabels is not None:
        labels = labels + sublabels # add labels of previous folders
    for folder in folders:
        create_dataset(os.path.join(input_dir, folder), sublabels=labels)
    for midifile in midifiles:
        filename = os.path.basename(midifile)
        print(filename)
        f_labels = labels + to_labels(filename) # add labels contained in filename
        f_labels = set(f_labels) # unique labels       
        labels_file.write('{},{}\n'.format(filename, ';'.join(f_labels)))
        copyfile(os.path.join(input_dir, midifile), os.path.join(DATA_DIR, filename))
    labels_file.close()

def replace_labels():
    """ 'chpn -> chopin
    """
    pass

if __name__ == "__main__":
    print(art)
    print(message)
    #create_dataset('download/test')
    print(get_labels())
    #to_midifile(matrix, 'example', path=OUTPUT_DIR)
    #data = get_data()
    #for e in data:
    #    print(e.shape)
    
    
