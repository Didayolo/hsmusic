import sys
sys.path.append('../')
import hsmusic
import numpy as np
from tqdm import tqdm
import autopandas as apd

def crop_data(data, sequence_length=100):
    """ TODO: take several parts of the piece
    """
    for i in range(len(data)):
        if data[i].shape[0] > sequence_length: # crop
            data[i] = data[i][:sequence_length, :, :]
        else: # pad
            padded = np.zeros((sequence_length, 78, 2))
            padded[:data[i].shape[0],:data[i].shape[1],:data[i].shape[2]] = data[i]
            data[i] = padded
    return np.stack(data)

def crop_data_bis(data, sequence_length=100):
    """ TODO: take several parts of the piece
    """
    new_data = []
    for i in range(len(data)):
        if data[i].shape[0] > sequence_length: # crop
            new_data.append(data[i][:sequence_length, :, :])
    return np.stack(new_data)

def simplify_data(data):
    return data[:,:,:,0]

def binarize(a, threshold=0.5):
    """ Binarize np.array
    """
    return np.where(a > threshold, 1, 0)
