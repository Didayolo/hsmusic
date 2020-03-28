# Functions for data formatting, etc.

# hsmusic.py should contains only "user" functions.

import os
import pandas as pd
import unicodedata
import re
from shutil import move

DATA_DIR = 'data'
OUTPUT_DIR = 'output'
LABELS_DIR = 'labels'
LABELS_FILENAME = os.path.join(LABELS_DIR, 'labels.csv')
NOT_LABELS_FILENAME = os.path.join(LABELS_DIR, 'not_labels.csv')
REPLACE_LABELS_FILENAME = os.path.join(LABELS_DIR, 'replace_labels.csv')
ADD_LABELS_FILENAME = os.path.join(LABELS_DIR, 'add_labels.csv')

def standardize(string):
    """ Convert a character string into another one in a standard format for naming.
        Converts to lowercase, removes non-alpha characters, and converts spaces to hyphens.
        Example: 'La Marseillaise' -> 'la_marseillaise'.
    """
    string = str(string)
    string = unicodedata.normalize('NFKD', string) #.encode('ascii', 'ignore').decode('ascii')
    string = re.sub('[^\w\s-]', '', string).strip().lower()
    string = re.sub('[-\s:]+', '_', string)
    return string

def to_labels(midifile):
    """ Read metadata from a MIDI file and return a list of labels.
        From filename: bach_partita.mid -> 'bach', 'partita'
        From MIDI: Number of voices, Time signature, etc.
    """
    #pattern = midi.read_midifile(midifile)
    #metadata = pattern[0]
    filename = standardize(os.path.basename(midifile))
    filename = filename.replace('mid', '')
    filename = filename.replace('midi', '')
    labels = filename.split('_')
    return list(set(labels))

def get_labels():
    """ Read labels file and return a DataFrame.
        Labels of one example are separated with ';'.
        :return: DataFrame ['FileName', 'Labels']
        :rtype: pd.DataFrame
    """
    return pd.read_csv(LABELS_FILENAME, header=0, index_col=None)

def get_not_labels():
    """ Return a list of tags to not consider as labels.
        :rtype: pd.DataFrame
    """
    return pd.read_csv(NOT_LABELS_FILENAME, header=None, index_col=None)

def get_replace_labels():
    """ Mapping of replacements.
        e.g. 'chpn' -> 'chopin'.
        :return: DataFrame ['Current', 'New']
        :rtype: pd.DataFrame
    """
    return pd.read_csv(REPLACE_LABELS_FILENAME, header=0, index_col=None)

def get_add_labels():
    """ Pairs of labels contained one in another.
        e.g. if labels 'bach' is present, adds 'baroque'.
        :return: DataFrame ['Current', 'New']
        :rtype: pd.DataFrame
    """
    return pd.read_csv(ADD_LABELS_FILENAME, header=0, index_col=None)

def create_dataset(input_dir, sublabels=None):
    """ Scan input_dir folder and execute create_dataset recursively.
        Read labels from directory names, filenames and MIDI files.
        Write labels in labels file.
    """
    print('Initializing dataset...')
    # standardize folder name
    new_input_dir = os.path.join(os.path.dirname(input_dir), standardize(os.path.basename(input_dir)))
    move(input_dir, new_input_dir) # rename
    input_dir = new_input_dir
    # create labels file
    if not os.path.isfile(LABELS_FILENAME):
        labels_file = open(os.path.join(LABELS_FILENAME), 'w') # in root dir
        labels_file.write('FileName,Labels\n')
        labels_file.close()
    labels_file = open(os.path.join(LABELS_FILENAME), 'a')
    #if not os.path.exists(DATA_DIR):
    #    os.makedirs(DATA_DIR) # create data dir
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
        create_dataset(os.path.join(input_dir, folder), sublabels=labels) # recursive call
    for midifile in midifiles:
        filename = standardize(os.path.basename(midifile))[:-3] + '.mid'
        print(filename)
        f_labels = labels + to_labels(filename) # add labels contained in filename
        f_labels = set(f_labels) # unique labels
        filename_path = os.path.join(input_dir, filename)
        labels_file.write('{},{}\n'.format(filename_path, ';'.join(f_labels)))
        move(os.path.join(input_dir, midifile), filename_path) # rename midifile
    labels_file.close()

def get_labels_distribution(labels):
    """ Read labels file and return the labels distribution.
        :return: Number of occurences for each label.
        :rtype: dict
    """
    labels = labels['Labels']
    dist = dict()
    for line in labels:
        for label in line.split(';'):
            if label in dist:
                dist[label] += 1
            else:
                dist[label] = 1
    return dist

def clean_labels(labels):
    """ 1. Not labels:     'midi' -> ''
        2. Replace labels: 'chpn -> chopin
        3. Add labels:     'bach' -> 'bach,baroque'
        4. Delete unshared labels (only one occurence).
    """
    print('Cleaning labels...')
    # read labels file
    not_labels = get_not_labels()
    replace_labels = get_replace_labels()
    add_labels = get_add_labels()
    for index, row in labels.iterrows():
        labels_list = row['Labels'].split(';')
        # 1. delete "not labels"
        labels_list = [x for x in labels_list if not not_labels.isin([x]).any().bool()]
        # 2. replace labels
        for i, r in replace_labels.iterrows():
            labels_list = [x.replace(r['Current'], r['New']) for x in labels_list]
        # 3. add labels
        to_add = []
        for i, r in add_labels.iterrows():
            if r['Current'] in labels_list:
                to_add.append(r['New'])
        labels_list = labels_list + to_add
        labels_list = list(set(labels_list)) # delete doubles
        labels.at[index, 'Labels'] = ';'.join(labels_list) # update df
        #row['Labels'] = ';'.join(labels_list)
    # 4. delete label linked to only one example
    dist = get_labels_distribution(labels)
    only_once = [] # list of tags occuring only once
    for key in dist.keys():
        if dist[key] == 1:
            only_once.append(key)
    for index, row in labels.iterrows(): # another loop over labels
        labels_list = row['Labels'].split(';')
        labels_list = [x for x in labels_list if x not in only_once]
        row['Labels'] = ';'.join(labels_list)
    #labels.to_csv(LABELS_FILENAME, index=False) # save labels file
    labels.to_csv('test.csv', index=False) # TMP TODO
    # some lines disappear?

def delete_duplicates():
    """ Delete MIDI file duplicates and merge their labels.
    """
    # compare binary matrices?
    pass
