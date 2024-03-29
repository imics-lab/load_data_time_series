# -*- coding: utf-8 -*-
"""load_data_transforms.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1BHrAphWsMKjP9bjL3dXn-f58P4_lq-2q

#load_data_transforms.ipynb

This is the common code that can be applied to all datasets after the conversion to the standard Intermediate Representation 1 (IR1) dataframe.

Set interactive to true to run the Jupyter Notebook version.  Note most of the calls are setup to test the functions, not process the entire dataset, to do that set interactive to false and run all so that main executes.   This notebook can be saved and run as a python file as well.


<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

[Lee B. Hinkle](https://userweb.cs.txstate.edu/~lbh31/), Texas State University, [IMICS Lab](https://imics.wp.txstate.edu/)  
TODO:
* This is in-progress - current focus is on the Gesture dataset so testing will need to be done with the others.
* Issue with !gdown not running in a function is a pain.
* assign_ints_ir1_labels() seems to still return an int64 instead of int8
* get_ir2_from_ir1(df) only handles a single 'label' column, needs update based on the keys in the label_map dict.  Sub column is also hardcoded in this function, should at least check for 'sub' and 'subject'
* Same basic issue for get_ir2_y_string_labels(), it needs to be updated to handle multilabel cases.
* Needs at least a basic _init_ unit test to be able to generate some output when checking as a .py
"""

import os
import shutil #https://docs.python.org/3/library/shutil.html
from shutil import unpack_archive # to unzip
import time
import pandas as pd
import numpy as np
from numpy import savetxt
from tabulate import tabulate # for verbose tables, showing data
from tensorflow.keras.utils import to_categorical # for one-hot encoding
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
from time import gmtime, strftime, localtime #for displaying Linux UTC timestamps in hh:mm:ss
from datetime import datetime, date
import urllib.request # to get files from web w/o !wget
import matplotlib.pyplot as plt
from scipy import stats as st # for assigning labels as mode of sliding window

"""# Global Parameters"""

# environment and execution parameters
my_dir = '.' # replace with absolute path if desired
dataset_dir = os.path.join(my_dir,'gesture_phase_dataset') # Where dataset will be unzipped

interactive = True # for exploring data and functions interactively
verbose = True

# dataset parameters
# These are here for debugging, need to be set for each dataset
# since these values very much depend on the nature of the data and are also
# important hyperparameters for evaluation.
time_steps = 32 
stride = 8

# example of how to load these transforms and set params in loader:
# import load_data_transforms as xform
# xform.time_steps = 96 # three seconds at 32Hz
# xform.stride = 32 # one second step for each sliding window

interactive = False # don't run if interactive, automatically runs for .py version
verbose = False # to limit the called functions output, overwrite per above

"""# Get IR1 dataframes for interactive testing.
IMPORTANT: this code must be commented out when saving as .py!

There is also nothing super special about the GPS dataset, it was just the one I was working on when I moved many of this functions to this file.
"""

if interactive:
    print ("What?")
#Weird - gdown fails when called inside function.  Hack for now...

# !gdown "11OWxTejlTlR53s3RZbSNZdyMdFiN4dZl&confirm=t" # Gesture Phase Raw IR1s in zip
# shutil.unpack_archive('Gesture_Phase_Raw_IR1.zip', my_dir, 'zip')
# ir1_df = pd.read_pickle("a1_raw.pkl")
# ir1_df['label']=ir1_df['label'].astype('category') # stored test file has strings
# display(ir1_df.info())

# ir1_df.head(5)

"""# This cell is a utility function from load_data_utils.py
It shortens the interactive code but the entire utils library is not needed.
"""

def tabulate_numpy_arrays(dict_name_npy):
    """Returns a string of tabulated data for numpy arrays passed as dictionary.
    args: dictionary format of {"npy_array_name":npy_array,...}.
    This one is pretty narrowly tested, mostly for trainX, testy etc."""
    # it seems silly to pass the variable name as a string, but I haven't found
    # a method that is portable/callable to get the variable name.
    from tabulate import tabulate
    headers = ("array","shape", "data type")
    meta_data = []
    for i in dict_name_npy :
        meta_data.append ((i,str(dict_name_npy[i].shape),str(dict_name_npy[i].dtype)))
    return(tabulate(meta_data, headers=headers))

"""# IR1 Pandas Dataframe Transforms
Much of the conversion from raw data and/or csv files to IR1 is dataset unique but there are several IR1 transforms that are useful for multiple datasets and plotting etc.
"""

def assign_ints_ir1_labels(df, label_mapping_dict):
    """Uses the mapping in the passed dictionary to assign integers to each
    string value predictably.  This is important because all labels may not
    be represented in each IR1 and strings take up too much room in IR2.
    Args:
        df - an IR1 dataframe with categorical label column
        label_mapping_dict - dict of dicts for each label column. See code.
    Returns:
        df - an updated IR1+ dataframe"""
    # Want to predictably convert the label strings into integers.
    # The sklearn label encoder is certainly an option but already have
    # a Pandas dataframe.   More importantly I want to encode the values
    # using all possible options not just the ones present in this particular
    # dataframe.   That means building a dictionary of the label mappings
    # which may even include labels not in the dataset at all, such as the
    # case with PSG-Audio.   Finally, I want to avoid ever having strings in the
    # numpy arrays - not an issue for small datasets but a big memory user
    # for larger ones.
    # Credit to this nice writeup https://pbpython.com/categorical-encoding.html
    if verbose:
        print("assign_ints_ir1_labels() converting categorical strings to ints")
    for label_name in label_mapping_dict: 
        if verbose:  
            print("df["+label_name+"] value counts before")
            print(df[label_name].value_counts())
        df[label_name] = df[label_name].replace(label_mapping_dict[label_name])
        df[label_name]=df[label_name].astype('int8') # force smaller type
        if verbose:
            print("df["+label_name+"] value counts after")
            print(df[label_name].value_counts())
    return df
if interactive:
    # This label mapping for Gesture-Phase-Segmentation dataset is in the order
    # of the readme.txt.  A second label entry can be added - see url above.
    label_map_gps = {"label":     {"Rest": 0, "Preparation": 1, "Stroke": 2,
                                   "Hold": 3, "Retraction": 4}}
    ir1_df = assign_ints_ir1_labels(ir1_df, label_mapping_dict = label_map_gps)

def convert_ir1_labels_to_strings(df,label_map):
    """This method is derived from the previous IR2 version in xforms.
    It is basically the reverse of assign_ints_ir1_labels()
    It was developed for Leotta where the raw labels are integer encoded.
    args:
        df - an IR1 dataframe with integer encoded lables
        label_map - dict with key = string, item = cooresponding int 
    returns:
        df - with categorical string labels"""
    # this seems to work but only when run once?   Needs to be checked and
    # moved to xforms notebook
    str_to_key_dict = label_map['label']
    key_to_str_dict = dict([(value, key) for key, value in str_to_key_dict.items()])
    
    if verbose:
        "Converting integer encoded labels to strings"
        print(str_to_key_dict)
        print(key_to_str_dict)
        print("Labels and counts before conversion")
        print(df['label'].value_counts())

    df['label'] = df['label'].map(key_to_str_dict)
    df['label'] = df['label'].astype('category')

    if verbose:
        print("Labels and counts after conversion")
        print(df['label'].value_counts())

    return df
if interactive:
    df_string = convert_ir1_labels_to_strings(df = ir1_df, label_map = label_map_gps)
    df_string.info()

def to_fixed_ir1_timedelta(df_in, new_time_step='50ms'):
    """resamples an IR1 dataframe to new_time_step.  Labels must be int not
    categorical strings.  Will  return NaN per resample method (happens on
    irregular samples). 'label' and 'sub' columns resample to floats and are
    typed back to int16
    args:
        df_in - an IR1 format dataframe
        new_time_step - string of pandas compatible times e.g. '50ms'
    returns:
        resampled pandas dataframe
    Note this has only been tested as a downsample.  Also if the same sample
    rate is given it can be used to 'correct' sample jitter in phone data"""
    orig_rows = len(df_in.index)
    df_out = df_in.resample(new_time_step).mean()
    df_out = df_out.interpolate() #linear interpolation for nan
    df_out['label'] = df_out['label'].astype(np.int8) # change from float to int
    df_out['sub'] = df_out['sub'].astype(np.int8) # change from float to int
    if verbose:
        print("Resampled at ",new_time_step,": Original/New # rows = ",orig_rows,len(df_out.index))
    return df_out
if interactive:
    df_temp = to_fixed_ir1_timedelta(ir1_df,new_time_step='20ms')
    df_temp.info()

def drop_ir1_columns(df, drop_col_list):
    """Used to remove IR1 columns, typically channels or labels that are not
    required.   Benefit is that IR1 dataframes have named columns and by doing
    this early it will save time and memory later.  There is a similar transform
    for IR2/IR3 numpy arrays.   Hint:  To display full column list call with
    empty drop_col_list and verbose = True
    Args:
        df = an IR1 format dataframe
        drop_column_list = list of columns to drop ex ['accel_x','accel_y']
    Returns:
        df = updated IR1 sans columns"""
    # this was originally in PSG-Audio - simple but minimally tested because I'm
    # afraid there will be too many other dependencies that need to change.
    # Updated/tested a version in Leotta before move into xforms.
    # TODO:  a lot of error checking should be added here including reporting
    # channels dropped and if a channel to be dropped wasn't found.
    temp_all_cols = list(df)
    keep_ch_list = [x for x in temp_all_cols if x not in drop_col_list]
    if verbose:
        print('drop_ir1_columns')
        print('All',len(temp_all_cols),'IR1 columns:', temp_all_cols)
        print('Dropping',len(drop_col_list),'columns:', drop_col_list)
        print('Remaining',len(keep_ch_list),'columns:', keep_ch_list)
    df = df[keep_ch_list]
    return df
if interactive:
    example_drop_list = ['lhx','lhy','lhz','lwx','lwy','lwz']
    display(ir1_df.head())
    ir1_df = drop_ir1_columns(ir1_df, drop_col_list = example_drop_list)
    ir1_df.info()
    display(ir1_df.head())

"""# Start of IR2 (Numpy Array) transforms"""

def get_ir2_from_ir1(df):
    """slice the IR1 dataframe into sliding window segments of
    time_steps length and return X, y, sub, ss_times ndarrays.
    If stride = time_steps there is no overlap of the sliding window.
    This version does not use append, better for RAM
    df: pandas datetime indexed dataframe columns - channel(s), label (as int), sub
    Global params used
    time_steps: number of samples in window, will discard a partial final window
    stride:  how far to move window, no overlap if equal to time_steps.
    Returns:
    X : ndarray of float32 shape(instances,timesteps,channels))
    y : ndarray of int8 labels of shape (instances, labels)
    sub : ndarray of int16 subject numbers shape (instances,1)
    ss_times : ndarray of datetime64 containing the start and stop time of 
        each window for label cleaning shape (instances, 2)
    channel_list : list of channels, df column names minus 'label' and 'sub'
    """    
    # this was copied from SHL with improved memory capabilities
    # TODO:  Update with multi-label version from PSG-Audio
    # TODO:  Should confirm IR1 datetimes are contiguous and warn if not.
    
    # the channel list is in dataframe but not in the numpy arrays
    channel_list = list(df.columns)
    channel_list.remove('label') # need to make sure this is defined for IR1
    channel_list.remove('sub') # ditto - should probably add a check
    if verbose:
        print('Channels in X:',channel_list)
    X = df[channel_list].to_numpy(dtype = 'float32')
    y = df['label'].to_numpy(dtype = 'int8') # doesn't work for strings
    sub = df['sub'].to_numpy(dtype = 'int16') # for datasets with sub #s > 255
    if verbose:
        print('X,y,sub array shapes before sliding window', X.shape, y.shape, sub.shape)
    #https://numpy.org/devdocs/reference/generated/numpy.lib.stride_tricks.sliding_window_view.html
    shapex = (time_steps,X.shape[1]) # samples (rows to include) and n-dim of original (all channels)
    shapey = (time_steps,) # samples (rows to include) and only one column
    shapesub = (time_steps,) # samples (rows to include) and only one column
    X = np.lib.stride_tricks.sliding_window_view(X, shapex)[::stride, :]
    X = X[:,0,:,:] # I admit I don't understand why this dimension appears...
    y = np.lib.stride_tricks.sliding_window_view(y, shapey)[::stride, :]
    sub = np.lib.stride_tricks.sliding_window_view(sub, shapesub)[::stride, :]
    # Build a numpy array of the start and stop timestamps for each sliding
    # window - the IR1 indices.  This is to help label cleaning if needed.
    timestamps_np = df.index.to_numpy(dtype = 'datetime64')
    shape_ts = (time_steps,) # samples (rows to include) and only one column
    timestamps_np = np.lib.stride_tricks.sliding_window_view(timestamps_np, shape_ts)[::stride, :]
    start_times = timestamps_np[:,0]
    stop_times = timestamps_np[:,-1]
    ss_times = np.column_stack((start_times,stop_times))
    if verbose:
        print('X,y,sub,ss_times array shapes after sliding window', X.shape, y.shape, sub.shape, ss_times.shape)
    return X, y, sub, ss_times, channel_list
if interactive:
    my_X, my_y, my_sub, my_ss_times, my_channel_list = get_ir2_from_ir1(ir1_df)
    print(tabulate_numpy_arrays({'my_X':my_X,'my_y':my_y,'my_sub':my_sub,'my_ss_times':my_ss_times}))
    print("Returned my_channel_list", my_channel_list)

def drop_ir2_nan(X, y, sub, ss_times):
    """removes sliding windows containing NaN, multiple labels, or multiple
    subject numbers.  Collapses y, sub to column arrays.
    Returns cleaned versions of X, y, sub, ss_times ndarrays"""
    # TODO:  This really should be split into multiple functions
    # Check for NaN
    nans = np.argwhere(np.isnan(X))
    num_nans = np.unique(nans[:,0]) #[:,0] just 1st column index of rows w/ NaN
    if verbose:
        print(num_nans.shape[0], "NaN entries found, removing")
    idx = ~np.isnan(X).any(axis=2).any(axis=1)
    # this warrants some explanation!
    # any(axis=1) and 2 collapses channels and samples
    # good axis explanation https://www.sharpsightlabs.com/blog/numpy-axes-explained/
    # the ~ negates so NaN location are now False in the idx which is then
    # used to filter out the bad windows below
    X = X[idx]
    y = y[idx]
    sub = sub[idx]
    ss_times = ss_times[idx]
    # repeat and confirm NaNs have been removed
    nans = np.argwhere(np.isnan(X))
    num_nans = np.unique(nans[:,0]) #[:,0] accesses just 1st column
    if (nans.size!=0):
        print("WARNING! Cleaned output arrays still contain NaN entries")
        print("execute print(X[99]) # to view single sample")
    return X, y, sub, ss_times
if interactive:
    my_X, my_y, my_sub, my_ss_times = drop_ir2_nan(my_X, my_y, my_sub, my_ss_times)  
    print(tabulate_numpy_arrays({'my_X':my_X,'my_y':my_y,'my_sub':my_sub,'my_ss_times':my_ss_times}))

def unify_ir2_labels(X, y, sub, ss_times, method = 'drop'):
    """For each sliding window examine all labels and either drop the window
     or assign all labels to the mode value.  Currently this works only for
     single labels, not multi-label datasets.  y and sub arrays are collapsed.
    Args:
     X,y,sub,ss_times:  IR2 df prior to collapsing X,y,sub,ss_times
     method: "drop" default - discard windows with mixed labels, typ train set
             "mode" - set all labels to mode value of labels in window
     returns X,y,sub,ss_times IR2 df with y & sub shapes now (instances, 1)"""
    # TODO: a threshold setting to determine which method would be nice.
    # TODO: test/fix the drop for multi-label case
    # Not happy with this code, must be a better way but it seems to work...
    # Also the interactive outputs should be integrated if verbose = True
    if method == 'drop':
        if verbose:
            print('Dropped windows(rows) with mixed labels:', sep = '',end='')
        idx = []
        for i in range(y.shape[0]):
            if np.all(y[i] == y[i][0]):
                idx.append(True)        
            else:
                idx.append(False)
                if verbose:
                    print(i,',',end='')
        X = X[idx]
        y = y[idx]
        sub = sub[idx]
        ss_times = ss_times[idx]
        if verbose:
            print()
        y = y[:,0] # collapse columns
        y = y[np.newaxis].T  # convert to single column array
    if method == 'mode':
        # scipy stats seems to be the best for mode
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mode.html
        y, counts = st.mode(y, axis = 1, keepdims = True)
        if (y.ndim == 3):
            y = y[:,0,:] # collapse if multi-label (found testing PSG-Audio)
        # TODO: the counts could be used for threshold to drop if not enough
    # check subs, warn if delta and collapse
    for i in range(sub.shape[0]):
        if np.all(sub[i] != sub[i][0]):
            print("WARNING:  Mixed subjects found in instance", i)
    sub = sub[:,0] # repeat for sub array
    sub = sub[np.newaxis].T
    return X, y, sub, ss_times
if interactive:
    my_X, my_y, my_sub, my_ss_times, all_channel_list = get_ir2_from_ir1(ir1_df)
    print("Labels and counts before drop (counts are divided by time-steps)")
    unique, counts = np.unique(my_y, return_counts=True)
    print (np.asarray((unique, counts/time_steps)).T)
    my_X, my_y, my_sub, my_ss_times = unify_ir2_labels(my_X, my_y, my_sub, my_ss_times, method = 'drop') 
    print("Labels and counts after drop")
    unique, counts = np.unique(my_y, return_counts=True)
    print (np.asarray((unique, counts)).T)
    print("Shapes after dropping windows with mixed labels")
    print(tabulate_numpy_arrays({'my_X':my_X,'my_y':my_y,'my_sub':my_sub,'my_ss_times':my_ss_times}))  
    # get new copy of the arrays since they have been altered.
    my_X, my_y, my_sub, my_ss_times, all_channel_list = get_ir2_from_ir1(ir1_df)
    my_X, my_y, my_sub, my_ss_times = unify_ir2_labels(my_X, my_y, my_sub, my_ss_times, method = 'mode')
    print("Labels and counts after mode assignment")
    unique, counts = np.unique(my_y, return_counts=True)
    print (np.asarray((unique, counts)).T)
    print("\nShapes with mode (should be unchanged in 1st dim = # instances)")
    print(tabulate_numpy_arrays({'my_X':my_X,'my_y':my_y,'my_sub':my_sub,'my_ss_times':my_ss_times}))

def get_ir2_y_string_labels(y,label_map):
    """This method reverses the int encoding applied to IR1 when run on an
    IR2/IR3 (sliding window numpy array).  The same label_map dict should be 
    used.  Currently only supports a single label, shape y = (instance,1)
    NOTE: This greatly increases the size of the array (for GPS dataset 44X)
    args:
        y - a IR2 or IR3 numpy array of int class labels, shape (instances,1)
        label_map - a dict containing the string to int encodings
    returns:
        y - a IR2 or IR3 numpy array of string class labels, shape (instances,1)"""
    # this code adapted from our Semi-Supervised-HAR.ipynb
    str_to_key_dict = label_map['label']
    key_to_str_dict = dict([(value, key) for key, value in str_to_key_dict.items()])
    
    if verbose:
        "Converting integer encoded labels back to original strings"
        print(str_to_key_dict)
        print(key_to_str_dict)
        print("Labels and counts before conversion")
        unique, counts = np.unique(y, return_counts=True)
        print (np.asarray((unique, counts)).T)

    y_labels = np.vectorize(key_to_str_dict.get)(y)
    y_labels = y_labels.reshape((-1, 1)) # reshape from (__,) to (__,1)
    
    if verbose:
        print("Labels and counts after conversion")
        unique, counts = np.unique(y_labels, return_counts=True)
        print (np.asarray((unique, counts)).T)
    return y_labels
if interactive:
    y_strings = get_ir2_y_string_labels(my_y, label_map = label_map_gps)
    print("y_strings.shape",y_strings.shape,"dtype",y_strings.dtype)
    print("First 5 entries", y_strings[:5])
    print("Size of original array",my_y.size * my_y.itemsize, "Bytes")
    print("Size of string array  ",y_strings.size * y_strings.itemsize, "Bytes")

def clean_ir2(X, y, sub, ss_times):
    """Deprecated, please use drop_ir2_nan and unify_ir2_labels directly.
    This version calls those two functions using drop for compatibility."
     """
    X, y, sub, ss_times = drop_ir2_nan(X, y, sub, ss_times)
    X, y, sub, ss_times = unify_ir2_labels(X, y, sub, ss_times, method = 'drop')
    return X, y, sub, ss_times
if interactive:
    # get new copy of the arrays since they have been altered.
    my_X, my_y, my_sub, my_ss_times, all_channel_list = get_ir2_from_ir1(ir1_df)
    my_X, my_y, my_sub, my_ss_times = clean_ir2(my_X, my_y, my_sub, my_ss_times)
    print(tabulate_numpy_arrays({'my_X':my_X,'my_y':my_y,'my_sub':my_sub,'my_ss_times':my_ss_times}))

def drop_label_ir2_ir3(X, y, sub, ss_times, label_to_drop):
    """removes windows with label = label_to_drop
    This is primarily used to remove invalid windows, such as 'unknown' = 99
    Returns updated version of X, y, sub, ss_times"""
    idx = []
    for i in range(y.shape[0]):
        if (y[i] == label_to_drop):
            idx.append(False)
        else:
            idx.append(True)
            #print('Discarding Row:', i)
    X = X[idx]
    y = y[idx]
    sub = sub[idx]
    ss_times = ss_times[idx]
    return X, y, sub, ss_times
if interactive:
    print("Label counts before drop")
    unique, counts = np.unique(my_y, return_counts=True)
    print (np.asarray((unique, counts)).T)
    print('X, y, sub array shapes before label drop', my_X.shape, my_y.shape, my_sub.shape)
    my_X, my_y, my_sub, my_ss_times = drop_label_ir2_ir3(my_X, my_y, my_sub,my_ss_times, 2)
    print("Label counts after drop")
    unique, counts = np.unique(my_y, return_counts=True)
    print (np.asarray((unique, counts)).T)
    print('IR2 shapes after label drop', my_X.shape, my_y.shape, my_sub.shape)
    headers = ("array","shape", "object type", "data type")
    mydata = [("my_X:", my_X.shape, type(my_X), my_X.dtype),
            ("my_y:", my_y.shape ,type(my_y), my_y.dtype),
            ("my_sub:", my_sub.shape, type(my_sub), my_sub.dtype),
            ("my_ss_times:", my_ss_times.shape, type(my_ss_times), my_ss_times.dtype)]
    print("IR2 array info after label drop")
    print(tabulate(mydata, headers=headers))

def get_ir3_from_dict(ir1_dict, label_map, label_method = 'drop'):
    """Processes a dictionary and combines the IR1 dataframes into a single
    IR3 set of numpy arrays.  Converts string labels to integers based on the
    passed label map.
    Params:
    ir1_dict: dict of IR1 dataframes key = IR1 source filename, item = IR1 df
    label_map: dict of labels (one entry per label column, most datasets will
         have only one with key = 'label'.  The item is a dict with keys of 
         all possible strings and item = corresponding int.)
    label_method: string if 'drop' all mixed labels will be discarded
                         if 'mode' all labels in window set to mode of labels
    Returns:
    X - ndarray (float32) of all channels
    y - ndarray (int8) of labels, for multi-label datasets # labels = # columns
    sub - ndarray (int16) subject number, int16 allows for sub nums > 255
    ss_times - ndarray (datetime64), start and stop time for sliding window
    xys_info - string, basically an autogenerated readme (needs work)
    """
    # NOTE - this is really hard to debug since an ir1_dict is required.
    # I've been just working on it in the TWRistAR loader paste the working code here.
    # Also this treats train and test the same - newer method being worked on
    # in the Leotta loader.
    df_list = list(ir1_dict) # ir1_dict.keys() returns a dict_keys type
    col_list = list(ir1_dict[df_list[0]].columns) # all columns in df
    label_list = list(label_map) # in case of multi-labeled dataset
    label_list.append('sub') # this really should be tested and not hard-coded
    # ref https://www.geeksforgeeks.org/python-remove-all-values-from-a-list-present-in-other-list/
    #ch_list = list(set(col_list) - set(label_list)) # don't do this - it reorders list!
    for i in label_list:
        try:
            col_list.remove(i)
        except ValueError:
            pass

    num_channels = len(col_list)
    ir3_X = np.zeros(shape=(1,time_steps,num_channels), dtype = 'float32')
    ir3_y = np.zeros(shape=(1,1),dtype='int8') # ints - strings take too much space
    #ir3_y = np.full(shape=(1,1), fill_value='n/a',dtype='<U10') # unicode 10 char
    ir3_sub = np.zeros(shape=(1,1),dtype='int16') # some dataset have sub# > 255
    ir3_ss_times = np.zeros(shape=(1,2),dtype='datetime64') # start/stop times of sliding window
    for ir1_fname, ir1_df in ir1_dict.items():
        if verbose:
            print('Processing ', ir1_fname)
        ir1_df = assign_ints_ir1_labels(ir1_df, label_mapping_dict = label_map)
        ir2_X, ir2_y, ir2_sub, ir2_ss_time, channel_list = get_ir2_from_ir1(ir1_df)
        ir2_X, ir2_y, ir2_sub, ir2_ss_time = drop_ir2_nan(ir2_X, ir2_y, ir2_sub, ir2_ss_time)
        ir2_X, ir2_y, ir2_sub, ir2_ss_time = unify_ir2_labels(ir2_X, ir2_y, ir2_sub, ir2_ss_time, method = label_method)
        ir2_X, ir2_y, ir2_sub, ir2_ss_time = drop_label_ir2_ir3(ir2_X, ir2_y, ir2_sub, ir2_ss_time, 99)
        ir3_X = np.vstack([ir3_X, ir2_X])
        ir3_y = np.vstack([ir3_y, ir2_y])
        ir3_sub = np.vstack([ir3_sub, ir2_sub])
        ir3_ss_times = np.vstack([ir3_ss_times, ir2_ss_time])
    #delete first row placeholders
    X = np.delete(ir3_X, (0), axis=0) 
    y = np.delete(ir3_y, (0), axis=0) 
    sub = np.delete(ir3_sub, (0), axis=0)
    sub = np.delete(ir3_sub, (0), axis=0)
    ss_times = np.delete(ir3_ss_times, (0), axis=0)

    xys_info = 'Needs work!\n'
    # xys_info += '\n'.join([str(elem) for elem in zip_flist]) # conv list to string
    # xys_info += '\nTime steps =' + str(time_steps) + ', Step =' + str(stride) + ', no resample\n'
    # xys_info += 'Final Shapes\n'
    # xys_info += "X shape " + str(X.shape) + " dtype = " + str(X.dtype) + "\n"
    # xys_info += "y shape " + str(y.shape) + " dtype = " + str(y.dtype) + "\n"
    # xys_info += "sub shape " + str(sub.shape) + " dtype = " + str(sub.dtype) + "\n"
    xys_info += "IR1 Channel names:" + str(channel_list) + "\n"
    # # Get final counts for label ndarray - not quite as easy as pandas df
    # xys_info += "Final Label Counts\n"
    # unique, counts = np.unique(y, return_counts=True)
    # xys_info += str(np.asarray((unique, counts)).T)
    # xys_info += "\nSamples per Subject\n"
    # unique, counts = np.unique(sub, return_counts=True)
    # xys_info += str(np.asarray((unique, counts)).T)
    return X, y, sub, ss_times, xys_info
# This was developed using TWristAR and Gesture-Phase-Segmentation but hard
# to have a mini-unit test here as it need the IR1 dictionary.
# if interactive:
#     X, y, sub, ss_times, xys_info = get_ir3_from_dict(ir1_dict, label_map = label_map_twristar, num_channels = 7)
#     headers = ("array","shape", "object type", "data type")
#     mydata = [("X:", X.shape, type(X), X.dtype),
#             ("y:", y.shape ,type(y), y.dtype),
#             ("sub:", sub.shape, type(sub), sub.dtype),
#             ("ss_time:", ss_times.shape, type(ss_times), ss_times.dtype)]
#     print(tabulate(mydata, headers=headers))
#     unique, counts = np.unique(y, return_counts=True)
#     print('Label Counts:\n',str(np.asarray((unique, counts)).T))
#     print(label_map_twristar)

def limit_channel_ir3(ir3_X, 
                      all_channel_list,
                      keep_channel_list):
    """Pass the full ir3_X array with all channels, the stored all_channel_list
    that was extracted from the ir1 dataframe column names, and a 
    keep_channel_list.  Matching channels will be kept, all others dropped."""
    # This would have been much easier at IR1 but that would precluded channel 
    # experiments and by channel feature representations.  I'm still torn on
    # whether dropping at IR1 would be better because it could be by column
    # name instead of list position.
    # For PSG-Audio I've been working on drop_ir1_columns function to delete
    # the known unused columns earlier in the process.
    # This is really new code, I'm leaving in some commented statements for now
    ch_idx = []
    # should add check here for channels not in list
    for i in keep_channel_list:
        ch_idx.append(all_channel_list.index(i)) 
    if verbose:
        print("Keeping X columns at index", ch_idx)
    new_X = ir3_X[:,:,ch_idx]
    return new_X
if interactive:
    print("all_channel_list", all_channel_list)
    print("starting X shape", my_X.shape)
    print("first row", my_X[0,0,:])
    my_new_X = limit_channel_ir3(my_X, all_channel_list,
                                 keep_channel_list = ['lhx', 'lhy', 'lhz'])
    print("ending X shape", my_new_X.shape)
    print("first row", my_new_X[0,0,:])