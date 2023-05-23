# -*- coding: utf-8 -*-
"""leotta_2021_load_dataset.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1NFjvOy6E7HNsvWj5VPQAfqN3yHRf70mk

#leotta_2021_load_dataset.ipynb

This is a loader for the Leotta et al. Activities of Daily Living dataset with ankle, hip, and wrist data.   Please see the paper [here](https://sepl.dibris.unige.it/publications/2021-leotta-CARE.pdf) and cite the original dataset if you use this in your work.

General load_data_time_series info is available at our [IMICS github repository](https://github.com/imics-lab/load_data_time_series)

Example usage:

    x_train, y_train, x_test, y_test = leotta_2021_load_dataset()
  

Developed and tested using colab.research.google.com
IMPORTANT a high RAM runtime is required. Select runtime > change type > shape = high RAM  
To save as .py version use File > Download .py.   Note that you will have to comment out the !gdown code and manually download the source zip file when running as .py.

Author:  [Lee B. Hinkle](https://userweb.cs.txstate.edu/~lbh31/), [IMICS Lab](https://imics.wp.txstate.edu/), Texas State University, 2023

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

TODOs:
* Integration of get_X_y_sub code and conversion to the more standard format in progress.
"""

import os
import shutil #https://docs.python.org/3/library/shutil.html
from shutil import unpack_archive # to unzip
import urllib.request # to get files from web w/o !wget
import requests #for downloading zip file
import pandas as pd
import numpy as np
import time
from datetime import datetime, date # to timestamp log file
# from tabulate import tabulate # for verbose tables, showing data
import matplotlib.pyplot as plt
# from tensorflow.keras.utils import to_categorical # for one-hot encoding
# from sklearn.model_selection import train_test_split
# from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder

"""# Load shared transform (xforms) functions and utils from IMICS Public Repo


"""

def get_web_file(fname, url):
    """checks for local file, if none downloads from URL.    
    :return: nothing"""
    if (os.path.exists(fname)):
        print ("Local",fname, "found, skipping download")
    else:
        print("Downloading",fname, "from", url)
        urllib.request.urlretrieve(url, filename=fname)

try:
    import load_data_transforms as xforms
except:
    get_web_file(fname = 'load_data_transforms.py', url = 'https://raw.githubusercontent.com/imics-lab/load_data_time_series/main/load_data_transforms.py')
    import load_data_transforms as xforms

try:
    import load_data_utils as utils  
except:
    get_web_file(fname = 'load_data_utils.py', url = 'https://raw.githubusercontent.com/imics-lab/load_data_time_series/main/load_data_utils.py')
    import load_data_utils as utils

"""# Global and Dataset Parameters"""

# environment and execution parameters
my_dir = '.' # replace with absolute path if desired
dataset_dir = os.path.join(my_dir,'dataset') # temp dir for processing

interactive = True # for exploring data and functions interactively
verbose = True

log_info = "" # a global to append dataset processing info

# dataset parameters, these are set as globals in the xforms code
xforms.time_steps = 300 # three seconds at 100Hz
xforms.stride = 300 # no overlap of the sliding windows

subj_alloc_dict = dict (train_subj = [1,2,7,8], valid_subj = [3,6], test_subj = [4,5])

# The label_map_<dataset> contains a mapping from strings to ints for all
# possible labels in the entire dataset.   This allows for predictable conversion
# regardless of the slices.
label_map_leotta = {"label":     {'OTHER':0,'RELAX':1,'KEYBOARD_WRITING':2,
                                  'LAPTOP':3,'HANDWRITING':4,'HANDWASHING':5,
                                  'FACEWASHING':6,'TEETHBRUSH':7,'SWEEPING':8,
                                  'VACUUMING':9,'EATING':10,'DUSTING':11,
                                  'RUBBING':12,'DOWNSTAIRS':13,'WALKING':14,
                                  'WALKING_FAST':15,'UPSTAIRS_FAST':16,
                                  'UPSTAIRS':17}} # from README.txt
# List of original channels to drop, torn whether this should be here or a 
# passed parameter.  Most often I use only vector magnitudes.                                
leotta_comp_accel = ['ankle_accel_x', 'ankle_accel_y', 'ankle_accel_z',
                     'hip_accel_x', 'hip_accel_y', 'hip_accel_z',
                     'wrist_accel_x', 'wrist_accel_y', 'wrist_accel_z']

# runs when saved as .py, skip cell if developing/debugging
interactive = False 
verbose = False # note this can be changed after import using xforms.verbose = True

# Please go to https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/G23QTS
# to read through the terms and also find the proper citations if you use this dataset.
# This is also where you can download directly if the link below fails.

# Next line must be commented out before saving as .py - then manual download
# is required.
#!gdown "1P5PIYeYvbfL4kQj-P2sm-JquUIddAxec&confirm=t" # ADL_Leotta_2021.zip

def unzip_leotta():
    """check for local copy, if none unzips the dataset structure in working_dir"""
    if (os.path.isdir(dataset_dir)):
        print("Using existing Leotta archive in", dataset_dir)
        return
    else:
        print("Unzipping Leotta 2021 dataset into", dataset_dir)
        zip_ffname = os.path.join(my_dir, 'ADL_Leotta_2021.zip')
        if (os.path.exists(zip_ffname)):
            print("Using source file", zip_ffname)
            shutil.unpack_archive(zip_ffname,dataset_dir,'zip')
        else:
            print("ERROR: ", zip_ffname, " not found")
            print("Go to https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/G23QTS")
            print("Click access dataset on right, accept terms, download zip and place in current directory")
            print("with filename ADL_Leotta_2021.zip, should be a 246.2MB zip file")
            return
if interactive:
    unzip_leotta()

def df_from_csv (
    sub_num, # 1 - 8
    sensor_loc): # ankle, hip, wrist
    """reads Leotta_2021 csv, returns df with accel x/y/z/ttl, label, sub_num
    args:
        sub_num (int) subject number from 1 to 8
        sensor_loc (string) sensor location ankle, hip, or wrist
    returns:
        An IR1 format dataframe, note labels are int encoded as in the raw dataset"""
    fnameX = sensor_loc + '_X_0' + str(sub_num) +  '.csv'
    fnamey = sensor_loc + '_Y_0' + str(sub_num) +  '.csv'
    ffnameX = os.path.join(dataset_dir, sensor_loc, fnameX)
    ffnamey = os.path.join(dataset_dir, sensor_loc, fnamey)
    if verbose:
        print ('df_from_csv processing: ', ffnameX, ffnamey)
    df = pd.read_csv(ffnameX)
    if (sensor_loc == 'wrist'): # Centrepoint device has different header name
        df.rename(columns={'Timestamp UTC': 'Timestamp'}, inplace=True)
    # the imported Timestamp is an object - need to convert to DateTime
    # in order to set the index to DateTime format.  Enables resampling etc.
    # Leaving these here - helpful to debug if leveraging this code!
        #print("*** Start ***")
        #print(type(df.index))
        #print(df.info(verbose=True))  
    df['Timestamp'] = pd.to_datetime(df['Timestamp']) 
    df.set_index('Timestamp', drop = True, inplace = True)
    if (sensor_loc != 'wrist'): # Centrepoint doesn't have non-accel columnns
        df = df.drop(['Temperature','Gyroscope X','Gyroscope Y','Gyroscope Z',
                      'Magnetometer X','Magnetometer Y','Magnetometer Z'], axis=1)
    df_sqd = df.pow(2)[['Accelerometer X','Accelerometer Y','Accelerometer Z']] #square each accel
    df_sum = df_sqd.sum(axis=1) #add sum of squares, new 1 col df
    df.loc[:,'accel_ttl'] = df_sum.pow(0.5)-1  # sqrt and remove 1g due to gravity
    del df_sqd, df_sum
    df.columns = [sensor_loc + '_accel_x', sensor_loc + '_accel_y', sensor_loc + '_accel_z', sensor_loc + '_accel_ttl']
    # tighten up the column types for space savings, probably should be function in utils or xforms
    # change to 32-bit, credit/ref https://stackoverflow.com/questions/69188132/how-to-convert-all-float64-columns-to-float32-in-pandas
    # Select columns with 'float64' dtype  
    float64_cols = list(df.select_dtypes(include='float64'))
    # The same code again calling the columns
    df[float64_cols] = df[float64_cols].astype('float32')
    # add activity numbers - number of rows are the same in this dataset
    # Why doesn't this work? df['label'] = pd.read_csv(ffnamey, dtype='Int64')
    dfy = pd.read_csv(ffnamey)
    df['label']=dfy['label'].to_numpy() # this works, above doesn't?
    df['label'] = df['label'].astype(np.int8) # change from float to int
    del dfy
    # add column with subject number
    df['sub'] = np.int8(sub_num)
    return df
if interactive:
    snum = 1
    df_ankle = df_from_csv(sub_num = snum, sensor_loc = 'ankle')
    df_hip = df_from_csv(sub_num = snum, sensor_loc = 'hip')
    df_wrist = df_from_csv(sub_num = snum, sensor_loc = 'wrist')
    display(df_ankle.info())
    display(df_hip.info())
    display(df_wrist.info())
    display(df_ankle.head())
    display(df_hip.head())
    display(df_wrist.head())

def df_from_one_sub (sub_num): # 1 - 8
    """reads 3 csv files for a single subject, combines an returns a single dataframe"""
    my_sub_num = sub_num # not sure necessary but easier to follow...
    df_ankle = df_from_csv(sub_num = my_sub_num, sensor_loc = 'ankle')
    df_hip = df_from_csv(sub_num = my_sub_num, sensor_loc = 'hip')
    #wrist is a bit more complicated since the sample rate is different
    df_wrist = df_from_csv(sub_num = my_sub_num, sensor_loc = 'wrist')
    df_wrist = xforms.to_fixed_ir1_timedelta(df_wrist,new_time_step='10ms')

    if ((df_ankle['label'].equals(df_hip['label']))
            and (df_ankle['sub'].equals(df_hip['sub']))
            and (df_ankle['label'].equals(df_wrist['label']))
            and (df_ankle['sub'].equals(df_wrist['sub']))) :
        if verbose:
            print('confirmed label and sub match - dropping from ankle and hip')
        df_ankle.drop(['label','sub'], axis=1, inplace=True)
        df_hip.drop(['label','sub'], axis=1, inplace=True)
    else:
        print('Error:  label and sub do not match, cannot combine dataframes')
        print('label match = ',df_ankle['label'].equals(df_hip['label']))
        print('sub match = ',df_ankle['sub'].equals(df_hip['sub']))
    df_temp = df_ankle.join(df_hip)
    df_final = df_temp.join(df_wrist)
    del df_temp
    df_final = xforms.convert_ir1_labels_to_strings(df = df_final, label_map = label_map_leotta)
    return df_final
if interactive:
    df_temp = df_from_one_sub (sub_num = 8)
    print(type(df_temp.index)) # should be DateTimeIndex
    print(df_temp.info(verbose=True))
    display(df_temp.head())

def get_leotta_ir1_dict():
    """reads the Leotta dataset and converts each "session file" to an IR1
    dataframe.  The goal here is to capture and convert all raw data into
    a 2D dataframe of rows = datetime index of each sample, columns = {channels,
    label(s), subject_num}.  Additional methods may be used to drop channels,
    and convert the string labels to mapped ints prior to switch to ndarrays.
    Args:
        none 
    Returns: a dict containing key = df_name and item = IR1 dataframes."""
    unzip_leotta()
    ir1_df_dict = dict() # an empty dictionary
    for i in range(1,9):
        ir1_name = "Leotta_Sub" + str(i)
        if verbose:
            print('get_leotta_ir1_dict is processing subject number', i, "as", ir1_name)
        df_temp = df_from_one_sub (sub_num = i)
        ir1_df_dict[ir1_name]=df_temp # key is root name in the file
    return ir1_df_dict
if interactive:
    verbose = False
    ir1_dict = get_leotta_ir1_dict()
    print('IR1 dataframes:',ir1_dict.keys())
    for df_name, df in ir1_dict.items():
        display(df.head())
        break # just want one
    verbose = True

"""# Convert IR1 dataframes to IR2 numpy arrays"""

# this should be moved to xforms once better tested.
def one_hot_by_label_dict(y, label_map_in):
    """One hot encode using dictionary so that the encoding is consistent
    even if some classes are missing from the train set (happens especially
    on X-fold Cross-Validation with sparse labels)
    params:
        y = numpy array with integer encoding
        label_map_in = dict with 'label' entry containing all possible classes
    returns:
        y = one-hot encoded ndarray, # columns = # classes in dict entry."""
    # ref: https://stackoverflow.com/questions/66644733/how-to-add-your-own-categories-into-the-onehotencoder
    if verbose:
        print("y shape into one_hot_by_label_dict is",y.shape)
        print("length of label map", len(label_map_in['label']), "equals the max number of classes")
        unique, counts = np.unique(y, return_counts=True)
        print("y counts\n",np.asarray((unique, counts)).T)
    #all_categories = np.array([str(i) for i in range(len(label_map['label']))])
    all_categories = [[str(i) for i in range(len(label_map_in['label']))]]
    enc = OneHotEncoder(categories = all_categories, sparse = False)
    y_oh = enc.fit_transform(y)
    y_oh = y_oh.astype('uint8')
    if verbose:
        print("Shape of returned array", y_oh.shape)
    return y_oh

def leotta_2021_load_dataset(
    incl_val_group = False, # split train into train and validate
    one_hot_encode = False, # make y into multi-column one-hot encoded
    ):
    """Loads the Leotta dataset zip from current directory, processes the data,
    and returns arrays by separating into _train, _validate, and _test arrays
    for X and y based on split_sub dictionary."""
    global log_info
    log_info = "Generated by leotta_2021_load_data.ipynb\n"
    today = date.today()
    log_info += today.strftime("%B %d, %Y") + "\n"
    log_info += "sub dict = " + str(subj_alloc_dict) + "\n"
    # Iterate through the IR1s in the dictionary, determine train-vs-test
    # then convert to IR2.  Much of this code was pulled from xform get_ir3_from_dict
    # which was used by TWristAR and heavily modified here.  This seems pretty 
    # close to being a generic version that could be put into transforms.
    label_map = label_map_leotta
    ir1_dict = get_leotta_ir1_dict()

    # Empty lists - it is better to make lists versus appending in the loop
    x_train_list, y_train_list, sub_train_list, ss_times_train_list = ([] for i in range(4))
    x_valid_list, y_valid_list, sub_valid_list, ss_times_valid_list = ([] for i in range(4))
    x_test_list, y_test_list, sub_test_list, ss_times_test_list = ([] for i in range(4))
    # iterate through the IR1 dataframes in the dictionary, process and allocate
    # to the train/valid/test lists.
    for df_name, df in ir1_dict.items():
        if verbose:
            print("leotta_2021_load_dataset is processing",df_name)
        df = xforms.assign_ints_ir1_labels(df,label_mapping_dict=label_map)
        df = xforms.drop_ir1_columns(df, drop_col_list = leotta_comp_accel)
        if (df['sub'].nunique() != 1):
            print("WARNING: IR1", df_name, "contains multiple subjects")
        sub_num = df['sub'].mode()[0] # since only one column it is a series not df
        x_temp, y_temp, sub_temp, ss_times_temp, ch_list_temp = xforms.get_ir2_from_ir1(df)
        if sub_num in subj_alloc_dict['train_subj']:
            if verbose:
                print('Allocating Subject',sub_num, 'to train')
            x_train_list.append(x_temp)
            y_train_list.append(y_temp)
            sub_train_list.append(sub_temp)
            ss_times_train_list.append(ss_times_temp)
        elif sub_num in subj_alloc_dict['valid_subj']:
            if verbose:
                print('Allocating Subject',sub_num, 'to valid')
            x_valid_list.append(x_temp)
            y_valid_list.append(y_temp)
            sub_valid_list.append(sub_temp)
            ss_times_valid_list.append(ss_times_temp)
        elif sub_num in subj_alloc_dict['test_subj']:
            if verbose:
                print('Allocating Subject',sub_num, 'to test')
            x_test_list.append(x_temp)
            y_test_list.append(y_temp)
            sub_test_list.append(sub_temp)
            ss_times_test_list.append(ss_times_temp)
        else:
            print('WARNING: Subject',sub_num,'not found in subj_alloc_dict, discarding')

    # https://stackoverflow.com/questions/27516849/how-to-convert-list-of-numpy-arrays-into-single-numpy-array
    x_train = np.vstack(x_train_list)
    y_train = np.vstack(y_train_list)
    sub_train = np.vstack(sub_train_list)
    ss_times_train = np.vstack(ss_times_train_list)
    x_train, y_train, sub_train, ss_times_train = xforms.unify_ir2_labels(x_train, y_train, sub_train, ss_times_train, method = 'drop')
    #print(utils.tabulate_numpy_arrays({'x_train':x_train, 'y_train':y_train, 'sub_train':sub_train, 'ss_times_train': ss_times_train}))

    x_valid = np.vstack(x_valid_list)
    y_valid = np.vstack(y_valid_list)
    sub_valid = np.vstack(sub_valid_list)
    ss_times_valid = np.vstack(ss_times_valid_list)
    x_valid, y_valid, sub_valid, ss_times_valid = xforms.unify_ir2_labels(x_valid, y_valid, sub_valid, ss_times_valid, method = 'drop')
    #print(utils.tabulate_numpy_arrays({'x_valid':x_valid, 'y_valid':y_valid, 'sub_valid':sub_valid, 'ss_times_valid': ss_times_valid}))

    x_test = np.vstack(x_test_list)
    y_test = np.vstack(y_test_list)
    sub_test = np.vstack(sub_test_list)
    ss_times_test = np.vstack(ss_times_test_list)
    x_test, y_test, sub_test, ss_times_test = xforms.unify_ir2_labels(x_test, y_test, sub_test, ss_times_test, method = 'mode')
    #print(utils.tabulate_numpy_arrays({'x_test':x_test, 'y_test':y_test, 'sub_test':sub_test, 'ss_times_test': ss_times_test}))

    if (one_hot_encode):
        y_train = one_hot_by_label_dict(y = y_train, label_map_in = label_map)
        y_valid = one_hot_by_label_dict(y = y_valid, label_map_in = label_map)
        y_test = one_hot_by_label_dict(y = y_test, label_map_in = label_map)
    
    if (incl_val_group):
        return x_train, y_train, x_valid, y_valid, x_test, y_test
    else:
        return np.vstack([x_train,x_valid]), np.vstack([y_train,y_valid]), x_test, y_test

if __name__ == "__main__":
    print("Downloading and processing Leotta 2021 dataset")
    print("Building dictionary of IR1 dataframes")
    ir1_dict = get_leotta_ir1_dict()
    print('IR1 dataframes:',ir1_dict.keys())
    # for df_name, df in ir1_dict.items():
    #     print(df.head())
    #     break # just want one
    
    x_train, y_train, x_test, y_test = leotta_2021_load_dataset()
    print("\nreturned arrays without validation group:")
    print("x_train shape ",x_train.shape," y_train shape ", y_train.shape)
    print("x_test shape  ",x_test.shape," y_test shape  ",y_test.shape)

    x_train, y_train, x_validation, y_validation, x_test, y_test = leotta_2021_load_dataset(incl_val_group=True)
    print("\nreturned arrays with validation group:")
    print("x_train shape ",x_train.shape," y_train shape ", y_train.shape)
    print("x_validation shape ",x_validation.shape," y_validation shape ", y_validation.shape)
    print("x_test shape  ",x_test.shape," y_test shape  ",y_test.shape)

    x_train, y_train, x_validation, y_validation, x_test, y_test = leotta_2021_load_dataset(incl_val_group=True, one_hot_encode = True)
    print("\nreturned arrays with validation group and one-hot encoded:")
    print("x_train shape ",x_train.shape," y_train shape ", y_train.shape)
    print("x_validation shape ",x_validation.shape," y_validation shape ", y_validation.shape)
    print("x_test shape  ",x_test.shape," y_test shape  ",y_test.shape)
    print(10*'-', "Contents of log_info", 10*'-')
    print(log_info)