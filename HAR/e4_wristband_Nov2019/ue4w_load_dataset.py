# -*- coding: utf-8 -*-
"""UE4W_load_dataset.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1jPv5A5d0hWUfQtEvbCUUlgVxfMGpW5Pb

#UE4W_load_dataset.ipynb

This is an enhancement of load_ue4w_demo.ipynb to include more of the load_dataset functions for the 'Unlabeled E4 Wristband' (UE4W) dataset which is on Zenodo https://doi.org/10.5281/zenodo.6898243

In particular this version adds the physiological data sensors in addition to the motion (acceleration) data.  Since this dataset is unlabeled only X, y, and sub arrays are returned - there is no train/valid/test split.  Also y and sub are only for compatibility, all y entries are set to "unk"nown and all sub entries are set to 1.

For updates please check our [IMICS lab git repository](https://github.com/imics-lab) 

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

[Lee B. Hinkle](https://userweb.cs.txstate.edu/~lbh31/), Texas State University, [IMICS Lab](https://imics.wp.txstate.edu/)  
TODO:
* Still work in progress
* get_ir3 function from TWristAR loader needs to be incorporated, currently this only loads a single file.
"""

import os
import shutil #https://docs.python.org/3/library/shutil.html
from shutil import unpack_archive # to unzip
#from shutil import make_archive # to create zip for storage
import requests #for downloading zip file
from scipy import io #for loadmat, matlab conversion
import time
import pandas as pd
import numpy as np
from numpy import savetxt
import matplotlib.pyplot as plt # for plotting - pandas uses matplotlib
from tabulate import tabulate # for g_verbose tables
from time import gmtime, strftime, localtime #for displaying Linux UTC timestamps in hh:mm:ss
from datetime import datetime
from datetime import timedelta
import urllib.request # to get files from web w/o !wget

my_dir = "." # replace with absolute path if desired
zip_baseURL = 'https://zenodo.org/record/6898244/files'
interactive = True # change to True if you want to run each cell function
# false with the ability to export to standalone .py not yet supported
global g_verbose # global, can be used in all functions without separate cfg.py
g_verbose = True
if interactive:
    print("work in progress")
    #zip_ffname = os.path.join(my_dir,zip_fname)
    #zip_fullURL = zip_baseURL + zip_fname
    #working_dir = my_dir + str.split(zip_ffname,'.')[1] # get rid of .zip

interactive = False # skip if running Jupyter notebook version

def get_ue4w_zipfile(zip_fname):
    """checks for local zipfile, if none downloads from zenodo repository
    after download will unzip the dataset into TWristAR directory.
    Assumes a global my_dir has been defined (default is my_dir = ".")
    :return: nothing"""
    zip_fullURL = 'https://zenodo.org/record/6898244/files/' + zip_fname
    zip_ffname = os.path.join(my_dir,zip_fname)
    if (os.path.exists(zip_ffname)):
        print ("Local zip file", zip_ffname, "found, skipping download")
    else:
        print ("Downloading", zip_fullURL)
        urllib.request.urlretrieve(zip_fullURL, filename=zip_fname)
    return
if interactive:
    zip_fname = '1568381971_A01F11.zip'
    get_ue4w_zipfile(zip_fname = zip_fname)

def unzip_e4_file(zip_ffname):
    """checks for local copy, if none unzips the e4 zipfile in dir ffname
    Note:  the files themselves do not contain subject info and there are
    multiple files e.g. ACC.csv, BVP,csv etc, in each zipfile.
    It is very important to further process the files with <fname>_labels.csv
    :param zip_ffname: the path and filename of the zip file
    :param working_dir: local (colab) directory where csv files will be placed
    :return: nothing"""
    working_dir = my_dir + str.split(zip_ffname,'.')[1] # get rid of .zip
    if (os.path.isdir(working_dir)):
        print("Skipping Unzip - Found existing directory", working_dir)
        return
    else:
        print("Unzipping e4 file in", working_dir)
        if (os.path.exists(zip_ffname)):
            shutil.unpack_archive(zip_ffname,working_dir,'zip')
        else:
            print("Error: ", zip_ffname, " not found, exiting")
            return
if interactive:
    zip_ffname = os.path.join(my_dir,zip_fname)
    unzip_e4_file(zip_ffname)

interactive = False

def df_from_e4_csv (ffname,col_labels):
    """"reads e4 ACC, BVP, EDA, and TEMP(erature) csv files, uses start time and
    sample rate to create time indexed pandas dataframe with columns.  
    Note the other e4 files have different format and must be read seperately. 
    :param ffname:  full filename e.g./content/temp/ACC.csv
    :col_labels: list of colums in csv - varies by type ['accel_x','accel_y...]
    :returns df: time indexed dataframe"""

    df = pd.read_csv(ffname, header=None)
    start_time = df.iloc[0,0].astype('int64') # first line in e4 csv
    sample_freq = df.iloc[1,0].astype('int64') # second line in e4 csv
    df = df.drop(df.index[[0,1]]) # drop 1st two rows, index is now off by 2
    # Make the index datetime first so code can be used for other data types
    # Having the index as datetime is required for pandas resampling
    # The start_time from the e4 csv file is forced to int64 which represents the
    # number of nanoseconds since January 1, 1970, 00:00:00 (UTC)
    # This is tricky - if float representation the join function may not work
    # properly later since the indexes must match exactly.
    # UTC_time is computed for each row, then made into required datetime format
    # that pandas will accept as an index
    df['UTC_time'] = (df.index-2)/sample_freq + start_time
    end_time = df['UTC_time'].iloc[-1]
    if g_verbose:
        print(ffname, "Sample frequency = ", sample_freq, " Hz")
        #show time in day month format, assumes same timezone
        print("File start time = ", strftime("%a, %d %b %Y %H:%M:%S", localtime(start_time)))  
        print("File end time   = ",strftime("%a, %d %b %Y %H:%M:%S", localtime(end_time)))
    #df = df.astype({'UTC_time': 'int64'}) # change future index from float64 to int64
    # this causes issues when trying to synch across sensors, if float then
    # some amount of error will be introduced.   May need to move earlier.
    df['datetime'] = pd.to_datetime(df['UTC_time'], unit='s')
    df.set_index('datetime',inplace=True)
    df = df.drop('UTC_time', axis=1)
    df.columns = col_labels
    return df
if interactive:
    # Note: IBI.csv is the inter-beat interval, a calculated value with a 
    # different format.  HR.csv is also calculated from BVP but format is same.
    working_dir = '1568381971_A01F11' # by zipfile name
    ffname = working_dir + '/ACC.csv'
    col_labels = ['accel_x', 'accel_y', 'accel_z']
    ir1_acc_df = df_from_e4_csv(ffname, col_labels)
    print("ACC dataframe shape", ir1_acc_df.shape)
    display(ir1_acc_df.head())

    ffname = working_dir + '/BVP.csv'
    col_labels = ['bvp']
    ir1_bvp_df = df_from_e4_csv(ffname, col_labels)
    print("BVP dataframe shape", ir1_bvp_df.shape)
    display(ir1_bvp_df.head())

    ffname = working_dir + '/EDA.csv'
    col_labels = ['eda']
    ir1_eda_df = df_from_e4_csv(ffname, col_labels)
    print("EDA dataframe shape", ir1_eda_df.shape)
    display(ir1_eda_df.head())

    ffname = working_dir + '/TEMP.csv'
    col_labels = ['p_temp']
    ir1_temp_df = df_from_e4_csv(ffname, col_labels)
    print("Temp dataframe shape", ir1_temp_df.shape)
    display(ir1_temp_df.head())

def process_e4_accel(df):
    """converts component accel into g and adds accel_ttl column
    per info.txt range is [-2g, 2g] and unit in this file is 1/64g.
    """
    df['accel_x'] = df['accel_x']/64
    df['accel_y'] = df['accel_y']/64
    df['accel_z'] = df['accel_z']/64
    df_sqd = df.pow(2)[['accel_x', 'accel_y', 'accel_z']] #square each accel
    df_sum = df_sqd.sum(axis=1) #add sum of squares, new 1 col df
    df.loc[:,'accel_ttl'] = df_sum.pow(0.5)-1  # sqrt and remove 1g due to gravity
    del df_sqd, df_sum
    return df
if interactive:
    ir1_acc_df = process_e4_accel(ir1_acc_df)
    display(ir1_acc_df.head())

def get_ir1_from_e4_dir(working_dir):
    """processes the four e4 sensor files into a single dataframe that
    is datetime indexed at 32Hz. Labeled columns are channels"""
    # Note: IBI.csv is the inter-beat interval, a calculated value with a 
    # different format.  HR.csv is also calculated from BVP but format is same.
    ffname = working_dir + '/ACC.csv'
    col_labels = ['accel_x', 'accel_y', 'accel_z']
    ir1_acc_df = df_from_e4_csv(ffname, col_labels)
    ir1_acc_df = process_e4_accel(ir1_acc_df)

    ffname = working_dir + '/BVP.csv'
    col_labels = ['bvp']
    ir1_bvp_df = df_from_e4_csv(ffname, col_labels)

    ffname = working_dir + '/EDA.csv'
    col_labels = ['eda']
    ir1_eda_df = df_from_e4_csv(ffname, col_labels)

    ffname = working_dir + '/TEMP.csv'
    col_labels = ['p_temp']
    ir1_ptemp_df = df_from_e4_csv(ffname, col_labels)

    ir1_df = ir1_acc_df.join(ir1_bvp_df, how="inner") # this drops bvp to 32Hz
    ir1_df = ir1_df.join(ir1_eda_df, how="outer") # stays at 32Hz, eda fill NaN
    ir1_df = ir1_df.join(ir1_ptemp_df, how="outer") # stays at 32Hz, p_temp fill NaN
    ir1_df = ir1_df.interpolate() # default is linear interpolation
    ir1_df = ir1_df.astype('float32') # no need for 64 precision with these sensors
    if g_verbose:
        print("IR1 full dataframe shape",ir1_df.shape)
        #print(ir1_df.head(10))
    return ir1_df
if interactive:
    ir1_df = get_ir1_from_e4_dir(working_dir)
    display(ir1_df.head(10))

if interactive:
    y1 = 1000 # starting y value (row #)
    y2 = 2000 # ending, plotting the whole dataframe is too much.
    ir1_df.iloc[499:1999].plot(subplots=True, figsize=(20, 10)) # yay Pandas

def show_tag_time(tag_ffname):
    """utility prints time marks from tags.csv to help with video sync 
    and labeling.   When this is run in colab it seems to be GMT regardless
    of timezone settings."
    :param tag_ffname: file to be processed e.g. /content/temp/tags.csv'
    :return: nothing"""
    try: 
        df_temp = pd.read_csv(tag_ffname, header=None)
    except:
        print("There are no tag marks in this file")
        return
    else:
        df_temp.columns = ['UTC_time']
        print ("    UTC_time          Local Time")
        for index, row in df_temp.iterrows():
            print(index, row['UTC_time'],
                strftime("%a, %d %b %Y %H:%M:%S", localtime(row['UTC_time'])))
# https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
# link to string formats for date and time
if interactive:
    print("Note: the tags for UE4W are not reliable for changes in activity")
    tag_ffname = working_dir + '/tags.csv'
    show_tag_time(tag_ffname)

def label_unlabeled_df (df, label = 'unk', sub = 0):
    """adds placeholder activity label and subject number columns to the
    dataframe.   This version for compatiblity only since it is unlabeled.
    :param df : time indexed dataframe from df_from_e4_csv method
    :label(str) : the label that will be applied to all rows
    :sub(int) : the sub number that will be applied to all rows
    :return : a dataframe with label and subject columns added"""
    df['label']= label # add column with safe value for labels
    df['sub'] = sub
    return df
if interactive:
    print("Adding placeholder label and sub info")
    ir1_df = label_unlabeled_df(ir1_df)
    display(ir1_df[5000:5005]) # head is meaningless since start is undefined

def get_ir2_from_ir1(df, time_steps, stride):
    """slice the IR1 dataframe into sliding window segments of
    time_steps length and return X, y, sub ndarrays.
    If stride = time_steps there is no overlap of the sliding window.
    This version does not use append, better for RAM
    df: pandas datetime indexed dataframe columns - channel(s), label, sub
    time_steps: number of samples in window, will discard a partial final window
    stride:  how far to move window, no overlap if equal to time_steps.
    """    
    # this was copied from SHL with improved memory capabilities
    # the channel list is in dataframe but not in the numpy arrays
    channel_list = list(df.columns)
    channel_list.remove('label') # need to make sure this is defined for IR1
    channel_list.remove('sub') # ditto - should probably add a check
    if g_verbose:
        print('Channels in X:',channel_list)
    X = df[channel_list].to_numpy(dtype = 'float32')
    y = df['label'].to_numpy(dtype='<U10')
    sub = df['sub'].to_numpy(dtype = 'int8')
    if g_verbose:
        print('X,y,sub array shapes before sliding window', X.shape, y.shape, sub.shape)
    #https://numpy.org/devdocs/reference/generated/numpy.lib.stride_tricks.sliding_window_view.html
    shapex = (time_steps,X.shape[1]) # samples (rows to include) and n-dim of original (all channels)
    shapey = (time_steps,) # samples (rows to include) and only one column
    shapesub = (time_steps,) # samples (rows to include) and only one column
    X = np.lib.stride_tricks.sliding_window_view(X, shapex)[::stride, :]
    X = X[:,0,:,:] # I admit I don't understand why this dimension appears...
    y = np.lib.stride_tricks.sliding_window_view(y, shapey)[::stride, :]
    sub = np.lib.stride_tricks.sliding_window_view(sub, shapesub)[::stride, :]
    # this was part of the clean function - rest is not needed for unlabeled
    y = y[:,0] # collapse columns
    y = y[np.newaxis].T  # convert to single column array
    sub = sub[:,0] # repeat for sub array
    sub = sub[np.newaxis].T
    if g_verbose:
        print('X,y,sub array shapes after sliding window', X.shape, y.shape, sub.shape)
    return X, y, sub, channel_list
if interactive:
    my_X, my_y, my_sub, all_channel_list = get_ir2_from_ir1(ir1_df, 96, 96)
    headers = ("array","shape", "object type", "data type")
    mydata = [("my_X:", my_X.shape, type(my_X), my_X.dtype),
            ("my_y:", my_y.shape ,type(my_y), my_y.dtype),
            ("my_sub:", my_sub.shape, type(my_sub), my_sub.dtype)]
    print("IR2 array info")
    print(tabulate(mydata, headers=headers))
    print("Returned all_channel_list", all_channel_list)

def limit_channel_ir3(ir3_X, 
                      all_channel_list,# = ['accel_x', 'accel_y', 'accel_z', 'accel_ttl', 'bvp', 'eda', 'p_temp'],
                      keep_channel_list):# = ['accel_ttl','bvp', 'eda', 'p_temp']):
    """Pass the full ir3_X array with all channels, the stored all_channel_list
    that was extracted from the ir1 dataframe column names, and a 
    keep_channel_list.  Matching channels will be kept, all others dropped.
    This would have been much easier at IR1 but that would precluded channel 
    experiments and by channel feature representations.
    This is really new code, I'm leaving in some commented statements for now"""
    ch_idx = []
    # should add check here for channels not in list
    for i in keep_channel_list:
        ch_idx.append(all_channel_list.index(i)) 
    if g_verbose:
        print("Keeping X columns at index", ch_idx)
    new_X = ir3_X[:,:,ch_idx]
    return new_X
if interactive:
    print("all_channel_list", all_channel_list)
    print("starting X shape", my_X.shape)
    print("first row", my_X[0,0,:])
    my_new_X = limit_channel_ir3(my_X, all_channel_list = all_channel_list,
                                 keep_channel_list = ['accel_ttl','p_temp'])
    print("ending X shape", my_new_X.shape)
    print("first row", my_new_X[0,0,:])

def ue4w_load_dataset(
    zip_flist = ['1568381971_A01F11.zip','1568436702_A01F11.zip','1568636849_A01F11.zip'],
    verbose = False,
    keep_channel_list = ['accel_ttl','bvp', 'eda', 'p_temp'],
    return_info_dict = False # return dict of meta info along with ndarrays
    ):
    global g_verbose
    g_verbose = verbose
    print("Iterating through", len(zip_flist), "files in ue4w dataset")
    # the hard coded 96 and 7 need to be fixed for other sample rates, channels
    ir3_X = np.zeros(shape=(1,96,len(keep_channel_list)), dtype = 'float32')
    ir3_y = np.full(shape=(1,1), fill_value='n/a',dtype='<U10') # unicode 10 char
    ir3_sub = np.zeros(shape=(1,1),dtype=np.uint8) # one subject number per entry
    for zip_fname in zip_flist:
        zip_ffname = os.path.join(my_dir,zip_fname)
        get_ue4w_zipfile(zip_fname)
        working_dir = my_dir + str.split(zip_ffname,'.')[1] # get rid of .zip
        unzip_e4_file(zip_ffname)
        print('Processing ', zip_ffname)
        my_df = get_ir1_from_e4_dir(working_dir)
        my_df = label_unlabeled_df(my_df)
        if g_verbose:
            print(my_df.head())
        my_X, y, sub, all_channel_list = get_ir2_from_ir1(my_df, 96, 96)
        my_X = limit_channel_ir3(my_X, all_channel_list= all_channel_list,
                              keep_channel_list = keep_channel_list) # default is to drop component accel
        ir3_X = np.vstack([ir3_X, my_X])
        ir3_y = np.vstack([ir3_y, y])
        ir3_sub = np.vstack([ir3_sub, sub])
    X = np.delete(ir3_X, (0), axis=0) 
    y = np.delete(ir3_y, (0), axis=0) 
    sub = np.delete(ir3_sub, (0), axis=0)
    sub = sub.astype(np.uint8) # convert from float to int
    return X, y, sub, keep_channel_list

"""# Main Function"""

if __name__ == "__main__":
    # Test the defaults
    X, y, sub, ch_list = ue4w_load_dataset()
    headers = ("Array","shape", "data type")
    mydata = [("X:", X.shape, X.dtype),
            ("y:", y.shape, y.dtype),
            ("sub:", sub.shape, sub.dtype)]
    print("\n",tabulate(mydata, headers=headers))
    print("Channels:", ch_list)

    # Test for single subject with only accel X shape should be (11926, 96, 1)
    X, y, sub, ch_list = ue4w_load_dataset(zip_flist = ['1568381971_A01F11.zip'],
                                           keep_channel_list = ['accel_ttl'])
    headers = ("Array","shape", "data type")
    mydata = [("X:", X.shape, X.dtype),
            ("y:", y.shape, y.dtype),
            ("sub:", sub.shape, sub.dtype)]
    print("\n",tabulate(mydata, headers=headers))
    print("Channels:", ch_list)

# run this cell to save the numpy arrays
if interactive:  
    readme = 'Unlabeled data from UE4W Repository, three files\n'
    readme += 'this version for fusion learned reps paper.\n'
    readme += 'Lee Hinkle, IMICS lab, December 13, 2022\n'
    readme += ' Array    shape           data type\n'
    readme += '        -------  --------------  -----------\n'
    readme += 'X:       (33523, 96, 4)  float32\n'
    readme += 'y:       (33523, 1)      <U10\n'
    readme += 'sub:     (33523, 1)      uint8\n'       
    readme += "         ['accel_ttl', 'bvp', 'eda', 'p_temp']'\n"

    with open(my_dir+'/README.txt', "w") as file_object:
        file_object.write(readme)
    np.save(my_dir + '/'+'X.npy',X)
    np.save(my_dir + '/'+'y.npy',y)
    np.save(my_dir + '/'+'sub.npy',sub)

"""# Example code that can be used to call this function when saved as .py"""

# def get_ue4w_loader():
#     """checks for local file, if none downloads from IMICS repository.
#     Assumes a global my_dir has been defined (default is my_dir = ".")
#     :return: nothing"""
#     ffname = os.path.join(my_dir,'ue4w_load_dataset.py')
#     if (os.path.exists(ffname)):
#         print ("Local twristar_load_dataset.py found, skipping download")
#     else:
#         print("Downloading twristar_load_dataset.py from IMICS git repo")
#         urllib.request.urlretrieve("https://raw.githubusercontent.com/imics-lab/load_data_time_series/main/HAR/e4_wristband_Nov2019/ue4w_load_dataset.py", filename="ue4w_load_dataset.py")
# if interactive:
#     get_ue4w_loader()

# from ue4w_load_dataset import ue4w_load_dataset
# # kludge for now - names should be derived from returned info from loader
# t_names = ['Downstairs', 'Jogging', 'Sitting', 'Standing', 'Upstairs', 'Walking']
# channel_list = ['accel_ttl','bvp','eda', 'p_temp'] # all channels to be used
#     x_train, y_train, x_valid, y_valid, x_test, y_test, log_info \
#                                 = twristar_load_dataset(
#                                     incl_val_group = True,
#                                     keep_channel_list = ch_list,
#                                     return_info_dict = True)
#     if verbose:
#         print (log_info)