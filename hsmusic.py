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
import os
from manage_dataset import *
from tqdm import tqdm

lower_bound = 24
upper_bound = 102

def to_matrix(midifile):
    """ Read a MIDI file and convert it into a binary matrix.
        :param midifile: MIDI filename string
        :return: Binary matrix of shape (?, upper_bound - lower_bound, 2)
        :rtype: np.ndarray
    """
    pattern = midi.read_midifile(midifile)
    timeleft = [track[0].tick for track in pattern]
    posns = [0 for track in pattern]
    statematrix = []
    span = upper_bound-lower_bound
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
                    if (evt.pitch < lower_bound) or (evt.pitch >= upper_bound):
                        pass
                        # print "Note {} at time {} out of bounds (ignoring)".format(evt.pitch, time)
                    else:
                        if isinstance(evt, midi.NoteOffEvent) or evt.velocity == 0:
                            state[evt.pitch-lower_bound] = [0, 0]
                        else:
                            state[evt.pitch-lower_bound] = [1, 1]
                elif isinstance(evt, midi.TimeSignatureEvent):
                    if evt.numerator not in (2, 4):
                        # We don't want to worry about non-4 time signatures. Bail early!
                        # print "Found time signature event {}. Bailing!".format(evt)
                        return np.asarray(statematrix)
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

def to_midi(statematrix, name="output.mid"):
    """ Write a binary matrix as a MIDI file under the specified name.
        :param statematrix: Binary matrix of shape (?, upper_bound - lower_bound, 2)
    """
    statematrix = np.asarray(statematrix)
    pattern = midi.Pattern()
    track = midi.Track()
    pattern.append(track)
    span = upper_bound-lower_bound
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
            track.append(midi.NoteOffEvent(tick=(time-lastcmdtime)*tickscale, pitch=note+lower_bound))
            lastcmdtime = time
        for note in onNotes:
            track.append(midi.NoteOnEvent(tick=(time-lastcmdtime)*tickscale, velocity=40, pitch=note+lower_bound))
            lastcmdtime = time
        prevstate = state
    eot = midi.EndOfTrackEvent(tick=1)
    track.append(eot)
    midi.write_midifile(name, pattern)

def contains_tag(tags_list, tag):
    """ Example: tags_list = 'bach;baroque;partita'
                 tag = 'bar'
                 return: False
    """
    return tag in tags_list # TODO can select string contained in another

def sample(labels, tags=None, numbers=None):
    """ ...
    """
    if tags is None:
        tags = ['']
    if isinstance(tags, str): # only one string instead of a list
        tags = [tags]
    if isinstance(numbers, int): # only one int instead of a list
        numbers = [numbers]
    if tags is not None and numbers is not None:
        if len(tags) != len(numbers):
            raise Exception('tags and numbers list length must match.')
    result = pd.DataFrame()
    for i in range(len(tags)):
        selection = labels[ [contains_tag(x, tags[i]) for x in labels['Labels']] ]
        if numbers is not None: # re-sampling
            replace = numbers[i] > len(selection)
            selection = selection.sample(n=numbers[i], replace=replace)
        result = pd.concat([result, selection]) # add to df
    return result

def get_data(tags=None, numbers=None, labels=None, return_filenames=False):
    """ Get data associated to specific labels.
        Default behaviour: get the whole dataset.
        Read midi files ...
        If save, create a .npy file with tensors from MIDI folder
        :param labels: As always, DataFrame [filename, list of tags]
        :param tags: List of wanted labels.
                       By default: all.
                       example: ['mozart', 'bach']
        :param numbers: List of integers with the same length as labels.
                        Numbers of examples to take from each label.
                        Sampling with replacement if the wanted number is greater than number of examples in the category.
        :param return_filenames: ...
        :return: Matrix of shape (n, ?, upper_bound - lower_bound, 2)
        :rtype: np.ndarray
    """
    print('Reading midi files...')
    if labels is None:
        labels = get_labels()
    data = []
    files = sample(labels, tags=tags, numbers=numbers)['FileName']
    for f in tqdm(files):
        try:
            data.append(to_matrix(f))
        except Exception as e:
            print('Failed to read {}.'.format(f))
            print(e)
    data = np.array(data)
    if return_filenames:
        return data, files
    return data

def get_filenames(tags=None, numbers=None):
    """ Return a pd.Series of all filenames/path given a list of tags.
    """
    labels = get_labels()
    filenames = sample(labels, tags=tags, numbers=numbers)['FileName']
    return filenames

def download():
    pass

def format(input_dir):
    """ Standardize data and labels from a folder with MIDI file.
        It is recommanded to have subdirectories representing various tags.
    """
    print('Formatting data...')
    create_dataset(input_dir)
    clean_labels(get_labels())

if __name__ == "__main__":
    print(art)
    print(message)

    print("Hint:")
    print("hsmusic.get_filnames('mozart')")
    print("hsmusic.get_filnames(['mozart', 'bach'])")

    # create dataset
    #format(DATA_DIR)

    #labels = get_labels()
    #print(get_labels_distribution(labels))

    #midi_file_example = labels['FileName'][0]
    #output_file_example = os.path.join(OUTPUT_DIR, 'output.mid')
    #print('Reading {}'.format(midi_file_example))
    #matrix = to_matrix(midi_file_example) # read file
    #print('Writing {}'.format(output_file_example))
    #to_midi(matrix, output_file_example) # write file

    # select and read data
    #print('Loading some music...')
    #data = get_data(labels, ['bach', 'mozart'], [10, 10])
    #for e in data:
    #    print(e.shape)
