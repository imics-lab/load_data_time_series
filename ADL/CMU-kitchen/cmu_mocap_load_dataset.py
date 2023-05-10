# -*- coding: utf-8 -*-
"""CMU-MoCap-load-dataset.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ScUg8WS_XfwsM6dzxost7MH6mMLEy24F

#CMU-MoCap-load-dataset.ipynb
This is a loader for the CMU grand challenge dataset with motion capture for subjects making several recipes.

The data used is obtained from kitchen.cs.cmu.edu and the data collection was funded in part by the National Science Foundation under Grant No. EEEC-0540865.

http://kitchen.cs.cmu.edu/main.php

If you use this dataset in your work please follow the dataset authors' citation request [here](https://www.ri.cmu.edu/publications/guide-to-the-carnegie-mellon-university-multimodal-activity-cmu-mmac-database/).

This is work in progress and frequently updated, please check the repository at our [IMICS Lab Github repository](https://github.com/imics-lab/load_data_time_series) for the latest.  Much appreciation to Vangelis Metsis and Alex Katrompas for the [initial loader](https://git.txstate.edu/imics-lab/tattend/tree/main/scripts) from which multiple methods have been derived.

<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

[Lee B. Hinkle](https://userweb.cs.txstate.edu/~lbh31/), Texas State University, [IMICS Lab](https://imics.wp.txstate.edu/)  
TODO:
* A lot.  This version is early work.
"""

import os
import shutil #https://docs.python.org/3/library/shutil.html
from shutil import unpack_archive # to unzip
import time
#import csv # probably not needed once download processes zip
import pandas as pd
import numpy as np
import tensorflow as tf
from numpy import savetxt
#from tabulate import tabulate # for verbose tables, showing data
from tensorflow.keras.utils import to_categorical # for one-hot encoding
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
import matplotlib.pyplot as plt # for plotting - pandas uses matplotlib
from time import gmtime, strftime, localtime #for displaying Linux UTC timestamps in hh:mm:ss
from datetime import datetime, date, timedelta
import urllib.request # to get files from web w/o !wget
import zipfile

def get_web_file(fname, url):
    """checks for local file, if none downloads from URL.    
    :return: nothing"""
    if (os.path.exists(fname)):
        print ("Local",fname, "found, skipping download")
    else:
        print("Downloading",fname, "from", url)
        urllib.request.urlretrieve(url, filename=fname)

"""# Load shared transform (xform) functions and utils"""

try:
    import load_data_transforms as xform
except:
    get_web_file(fname = 'load_data_transforms.py', url = 'https://raw.githubusercontent.com/imics-lab/load_data_time_series/main/load_data_transforms.py')
    import load_data_transforms as xform

try:
    import load_data_utils as utils  
except:
    get_web_file(fname = 'load_data_utils.py', url = 'https://raw.githubusercontent.com/imics-lab/load_data_time_series/main/load_data_utils.py')
    import load_data_utils as utils

"""# Setup environment and dataset parameters"""

# environment and execution parameters
my_dir = '.' # replace with absolute path if desired
ir1_dir = 'cmu_ir1' # this is where the raw data IR1s will be stored
#working_dir = 'psg_temp'
# if not os.path.exists(working_dir):
#     os.mkdir(working_dir)
interactive = True # for exploring data and functions interactively
verbose = True

# dataset parameters
all_channel_list = [] # this will get populated from the IR1 dataframe column names
xform.time_steps = 500 # IR1 dataframes are set to 100Hz
xform.stride = 500 # how far to move for next window, if = times_steps no overlap
# The label_map_<dataset> contains a mapping from strings to ints for all
# possible labels in the entire dataset.   This allows for predictable conversion
# regardless of the slices. The embedding of "label" is to allow for a common
# format for datasets with multiple labels such as PSG-Audio.   This list is 
# auto-generated by the interactive code near the end of the notebook.
label_map_cmu = {"label":     {"unknown":0,
        "take-big_bowl--":1,
        "take-measuring_cup_small--":2,
        "take-measuring_cup_big--":3,
        "none---":4,
        "take-fork--":5,
        "walk--to-fridge":6,
        "open-fridge--":7,
        "take-egg--":8,
        "close-fridge--":9,
        "walk--to-counter":10,
        "crack-egg--":11,
        "stir-egg--":12,
        "pour-water-into-measuring_cup_big":13,
        "pour-water-into-big_bowl":14,
        "take-oil--":15,
        "twist_off-cap--":16,
        "pour-oil-into-measuring_cup_small":17,
        "twist_on-cap--":18,
        "pour-oil-into-big_bowl":19,
        "put-oil-into-cupboard_bottom_right":20,
        "take-brownie_box--":21,
        "open-brownie_box--":22,
        "open-brownie_bag--":23,
        "take-scissors--":24,
        "pour-brownie_bag-into-big_bowl":25,
        "stir-big_bowl--":26,
        "take-baking_pan--":27,
        "open-cupboard_bottom_right--":28,
        "spray-pam--":29,
        "pour-big_bowl-into-baking_pan":30,
        "put-baking_pan-into-oven":31,
        "switch_on---":32,
        "take-pam--":33,
        "put-pam-into-cupboard_bottom_right":34,
        "read-brownie_box--":35,
        "put-scissors-into-drawer":36,
        "open-cupboard_top_right--":37,
        "open-cupboard_top_left--":38,
        "close-cupboard_top_right--":39,
        "close-cupboard_top_left--":40,
        "take-knife--":41,
        "put-knife-into-drawer":42,
        "open-drawer--":43}}

# setup a global readme so various methods can append info as needed
readme = 'This readme auto-generated by CMU-MoCap_load_dataset.ipynb\n'
readme += 'Executed on '
today = date.today()
readme += today.strftime("%B %d, %Y") + "\n"
readme += 'ref: https://github.com/imics-lab/load_data_time_series \n'

interactive = False # skip this cell, runs automatically for .py version

"""# CMU kitchen specific functions
Much appreciation to Vangelis Metsis and Alex Katrompas for the [initial loader](https://git.txstate.edu/imics-lab/tattend/tree/main/scripts) from which multiple methods have been derived.

"""

# Assign labels to each frame in the time synchronization data
def assign_label(frame_number, offset): # original
    for _, row in df_labels.iterrows():
        if row['start_frame'] <= frame_number - (offset - 1) <= row['end_frame']:
            return row['label']
    return 'unknown'

# Function to process the IMU data file
def process_data_file(file_path, archive):
    with archive.open(file_path) as f:
        # Get the sensor_ID from the first line of the file, e.g. "sensor_ID	2794"
        sensor_id = f.readline().decode('utf-8').split('\t')[1].strip()

        # Read the rest of the file into a Pandas DataFrame
        df = pd.read_csv(f, delim_whitespace=True)

    # Check if 'Count' column contains any string values
    if df['Count'].apply(lambda x: isinstance(x, str)).any():
        # Drop rows containing "ERROR_1--TIMEOUT" in the Count column
        df = df[~df['Count'].str.contains('ERROR')]

    # Convert SysTime to datetime object
    df['system_time'] = df['SysTime'].str.replace('_', ':')
    df['system_time'] = pd.to_datetime(df['system_time'], format='%H:%M:%S:%f')
    df.drop('SysTime', axis=1, inplace=True)

    # Remove sensor_ID row and reset the index
    # this next line is commented out, it shouldn't be here,
    # tested by vangelis, TODO test it more
    #df = df.drop(df.index[0]).reset_index(drop=True)

    # Drop the Count column
    df = df.drop('Count', axis=1)

    # Add sensor_ID as prefix to column names
    df.columns = [f'{sensor_id}_{col}' for col in df.columns]

    return df, sensor_id

# Function to merge two dataframes based on the nearest timestamp
def merge_dataframes(df1, df2):
    # Ensure system_time column in df1 is a datetime object
    if df1['system_time'].dtype != 'datetime64[ns]':
        df1['system_time'] = pd.to_datetime(df1['system_time'])

    # Find the system_time column in df2 and convert it to a datetime object
    for col in df2.columns:
        if col.endswith('_system_time'):
            if df2[col].dtype != 'datetime64[ns]':
                df2[col] = pd.to_datetime(df2[col])
            system_time_col = col

    # Sort df1 and df2 on the system_time columns
    df1 = df1.sort_values('system_time')
    df2 = df2.sort_values(system_time_col)

    # Merge the dataframes based on the nearest timestamp
    merged_df = pd.merge_asof(df1, df2, left_on='system_time', right_on=system_time_col, direction='nearest')

    # Drop the system_time column from the second dataframe
    merged_df = merged_df.drop(columns=[system_time_col])

    return merged_df

# define relative path
#RPATH = "../data/kitchen/"
RPATH = "./"

# Create the brownie_imu_data directory if it doesn't exist
if not os.path.exists(RPATH + 'brownie_imu_data'):
    os.makedirs(RPATH + 'brownie_imu_data')

# Define the subject IDs and start frames
subjects = {'S07': 508,
            'S08': 300,
            'S09':226,
            'S12':400,
            'S13':290,
            'S14':386,
            'S16':168,
            'S17':236,
            'S18':316,
            'S19':354,
            'S20':212,
            'S22':262,
            'S24':360}
if interactive:
    print("All subject and offsets:", subjects)
    print()

#for key in subjects:
df_labels = pd.DataFrame() # workaround so df_labels is avail for assign_labels
def get_cmu_imu_df(sub_key = 'S07'):
    global df_labels # same workaround from two lines up
    subject_id = sub_key
    subject_starting_frame = subjects[sub_key]
    if verbose:
        print("subject_id:", subject_id)
        print("subject_starting_frame", subject_starting_frame)
        print()

    # Define file paths
    video_zip_url = f'http://kitchen.cs.cmu.edu/Main/{subject_id}_Brownie_Video.zip'
    video_zip_file = f'{RPATH}brownie_imu_data/{subject_id}_Brownie_Video.zip'
    imu_zip_url = f'http://kitchen.cs.cmu.edu/Main/{subject_id}_Brownie_3DMGX1.zip'
    imu_zip_file = f'{RPATH}brownie_imu_data/{subject_id}_Brownie_3DMGX1.zip'
    annotation_zip_url = f'http://www.cs.cmu.edu/~espriggs/cmu-mmac/annotations/files/{subject_id}_Brownie.zip'
    annotation_zip_file = f'{RPATH}brownie_imu_data/{subject_id}_Brownie.zip'

    # Download the video data file if it hasn't been downloaded already
    if not os.path.exists(video_zip_file):
        if verbose:
            print(f'Downloading {video_zip_url}...')
        urllib.request.urlretrieve(video_zip_url, video_zip_file)
        if verbose:
            print(f'Saved {video_zip_file} to brownie_imu_data.')

    # Load the time synchronization data from the video data file into a Pandas DataFrame
    with zipfile.ZipFile(video_zip_file) as zipf:
        with zipf.open(f'STime7150991-time-synch.txt') as file:
            df_time_sync = pd.read_csv(file, sep=' ', header=None, usecols=[0, 4], names=['frame_number', 'system_time'])

    df_time_sync['frame_number'] = df_time_sync['frame_number'].str.replace('Frame:', '')
    df_time_sync['frame_number'] = df_time_sync['frame_number'].astype(int)
    if verbose:
        display(df_time_sync.head())

    # Download the 5 wired IMU data files if they haven't been downloaded already
    if not os.path.exists(imu_zip_file):
        if verbose:
            print(f'Downloading {imu_zip_url}...')
        urllib.request.urlretrieve(imu_zip_url, imu_zip_file)
        if verbose:
            print(f'Saved {imu_zip_file} to brownie_imu_data.')

    # Download the annotation file if it hasn't been downloaded already
    if not os.path.exists(annotation_zip_file):
        if verbose:
            print(f'Downloading {annotation_zip_url}...')
        urllib.request.urlretrieve(annotation_zip_url, annotation_zip_file)
        if verbose:
            print(f'Saved {annotation_zip_file} to brownie_imu_data.')

    # Load the annotation data from the annotation file into a Pandas DataFrame
    with zipfile.ZipFile(annotation_zip_file) as zipf:
        with zipf.open(f'{subject_id}_Brownie/labels.dat') as file:
            df_labels = pd.read_csv(file, sep=' ', names=['start_frame', 'end_frame', 'label'])

    df_labels['start_frame'] = df_labels['start_frame'].astype(int)
    df_labels['end_frame'] = df_labels['end_frame'].astype(int)
    if verbose:
        print('df_labels.head()')
        display(df_labels.head())
        print('df_labels.tail()')
        display(df_labels.tail())

    #this call fails after conversion to function - name 'df_labels' is not defined
    #workaround above was to declare a global, see first lines of this cell
    df_time_sync['label'] = df_time_sync['frame_number'].apply(assign_label, offset=subject_starting_frame)

    # Convert the system_time column to a datetime object
    df_time_sync['system_time'] = df_time_sync['system_time'].str.replace('_', ':')
    df_time_sync['system_time'] = pd.to_datetime(df_time_sync['system_time'], format='%H:%M:%S:%f')
    df_time_sync.head()

    # Save df_time_sync to a CSV file (for visual inspection)
    time_sync_data_file = f'{RPATH}brownie_imu_data/{subject_id}_time_sync_data.csv'
    df_time_sync.to_csv(time_sync_data_file, index=False)
    if verbose:
        print(f'Saved {time_sync_data_file} to brownie_imu_data.')

    # Open the zip file
    with zipfile.ZipFile(imu_zip_file, 'r') as archive:
        # Get the list of text files in the zip file
        file_paths = [file for file in archive.namelist() if file.endswith('.txt')]

        df_main = df_time_sync

        # Process each file in the zip file and merge it with df_main
        if verbose:
            print(f'Processing {len(file_paths)} files...')
        for file_path in file_paths:
            if verbose:
                print(f'Processing {file_path}...')
            df_temp, sensor_id = process_data_file(file_path, archive)
            df_main = merge_dataframes(df_main, df_temp)

    # This is the start of additional code Lee added.
    # Minor conversions to match IR1 format
    df_main.set_index('system_time',inplace=True) # make datetime indexed
    # commented out - passed as calling function when building IR1 dict
    # greatly speeds up plotting if index is set to frame column
    #df_main.drop(['frame_number'], axis=1, inplace=True)
    
    # Add subject number to dataframe
    sub_num = int(sub_key[1:]) # get rid of leading S and make int
    df_main['sub'] = sub_num
    df_main = df_main.astype({"sub": np.int16}) # sub nums are higher than 255

    # downsample 64-bit floats to 32-bit and force labels to categorical.
    # this reduces the size of the first dataframe from 345MB to 150MB.
    # this code originally pulled from latest TWRistAR loader
    # Select columns with 'float64' dtype  
    float64_cols = list(df_main.select_dtypes(include='float64'))
    if verbose:
        print("get_ir1_from_dir found these float64 cols - changing to float32")
        print(float64_cols)
    for i in float64_cols:
        df_main[i] = df_main[i].astype('float32')
    # Explicitly type the label columns to category.
    #df_main['label']=df_main['label'].astype('category')
    # Move the label to the end, right before sub, just for consistency
    df_main = df_main[[c for c in df_main if c not in ['label', 'sub']] 
       + ['label', 'sub']]
    return df_main

if interactive:
    df = get_cmu_imu_df()
    display(df.head())
    display(df.info())
    print("Unique subs - should only be one!", df['sub'].unique())
    print("Unique labels\n", df['label'].unique())

    # Save df_main to a CSV file
    # imu_data_file = f'{RPATH}brownie_imu_data/{subject_id}_imu_data.csv'
    # df_main.to_csv(imu_data_file, index=False)

def get_magnitude(df_xyz, unit_subtract = 0.0):
    """Converts Cartesian component values into vector length
    params:
    df_xyz = a dataframe with 3 columns representing x, y, z values
    unit_subtract = float used to convert to removed accel due to gravity (1 or 9.8 typically) 
    returns:
    df = a single column dataframe with the vector lengths.
    """
    num_cols = len(df_xyz.columns)
    if (num_cols != 3):
        print("ERROR: get_magnitude expected 3 column dataframe, found", num_cols)
        print(df.columns)
        return
    df_sqd = df_xyz.pow(2) #square each compenent
    series_sum = df_sqd.sum(axis=1) #add sum of squares, new 1 col df
    df_sum = series_sum.to_frame() # pandas sum function returns a series
    df_ttl = df_sum.pow(0.5) - unit_subtract # sqrt minus unit_subtract
    del df_sqd, df_sum
    return df_ttl
if interactive:
    df_temp = df[['2794_Accel_X', '2794_Accel_Y', '2794_Accel_Z']]
    df_mag = get_magnitude(df_temp, unit_subtract = 1.0)
    df_mag.columns = ['2794_Accel_TTL']
    df_all = pd.concat([df_temp, df_mag], axis = 1)
    display(df_all.head())

if interactive:
    # the datetimeindex plotting is super slow, much faster if converted to int64
    #df_all.index = pd.to_numeric(df_all.index, errors='coerce')
    df_all.index = df['frame_number']
    display(df_all.head())
    df_all.info()
    #df_all.iloc[0:17*30].plot(subplots=True, figsize=(20, 10)) # only 1st 17 secs
    df_all.plot(subplots=True, figsize=(20, 10))

def get_cmu_mocap_ir1_dict(incl_frame_num = False):
    """reads the CMU Motion Cap dataset brownie files and converts to an IR1
    dataframe.  The goal here is to capture and convert all raw data into
    a 2D dataframe of rows = datetime index of each sample, columns = {channels,
    label(s), subject_num}.  Additional methods may be used to drop channels,
    and convert the string labels to mapped ints prior to switch to ndarrays.
    Args:
        incl_frame_num - boolean, default = False, True enables faster plotting
    Returns: 
        dict containing key = df_name and item = IR1 dataframe."""
    print("Building dictionary of IR1 dataframes, with downloads this takes ~15 minutes to run")
    ir1_df_dict = dict() # an empty dictionary
    for key in subjects:
        ir1_fname = key+'_Brownie_3DMGX1'
        print('Processing',ir1_fname)
        df = get_cmu_imu_df(sub_key = key)
        if not incl_frame_num:
            df.drop(['frame_number'], axis=1, inplace=True)
        ir1_df_dict[ir1_fname]=df
    return ir1_df_dict
if interactive:
    verbose = False
    ir1_dict = get_cmu_mocap_ir1_dict(incl_frame_num=True)
    print('IR1 dataframes:',ir1_dict.keys())
    for df_name, df in ir1_dict.items():
        display(df.head())
        df.index = df['frame_number'] # too slow to use datetime index
        df.plot(subplots=True, figsize=(20, 30)) # Huge!
        break # just want one

# Trying to figue out the labels...
if interactive:
    all_label_df = pd.DataFrame()
    for ir1_df_name in list(ir1_dict):
        print(ir1_df_name)
        all_label_df = pd.concat([all_label_df,ir1_dict[ir1_df_name]])

        
    #df_s07 = ir1_dict['S07_Brownie_3DMGX1']
    print("Frames by Subject:\n", all_label_df['sub'].value_counts())
    print("Count of all labels:\n", all_label_df['label'].value_counts())

# OK, being lazy - try to build label dictionary automatically...
# I think this orders by appearance but not positive
if interactive:
    label_list = all_label_df['label'].unique()
    label_num = 0
    for item in label_list:
        line_str = '"' + item + '":' + str(label_num) +','
        print(line_str)
        label_num += 1

"""# Main is setup to be a demo and bit of unit test."""

verbose = False # otherwise a lot of output from main.

if __name__ == "__main__":
    print("Get dictionary of IR1 dataframes, this takes ~15 minutes to run with downloads")
    ir1_dict = get_cmu_mocap_ir1_dict()
    print('IR1 dataframes:',ir1_dict.keys())
    for df_name, df in ir1_dict.items():
        print(df.head()) # display option will fail when run as .py
        break # just want one