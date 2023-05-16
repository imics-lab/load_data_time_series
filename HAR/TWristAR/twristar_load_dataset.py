# -*- coding: utf-8 -*-
"""TWristAR_load_dataset.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Bv9_aEQ4kCEgzPZ-9zjnYUZvbgO_OtA4

#TWristAR_load_dataset.ipynb
Loads the raw e4 signals and .csv label files from the [Zenodo repository](https://zenodo.org/record/5911808) and returns train and test X/y numpy arrays.

The basic flow is:
* Download and unzip the dataset if not already present
* Convert each recording *session* into Intermediate Representation 1 (IR1) format - a datetime indexed pandas dataframe with columns for each channel plus the label and subject number.
* Put all IR1 dataframes into a dictionary with key = source filename
* Allocate the IR1s into train and test IR2s based on subject dictionary.  A single IR1 will generate multiple sliding window instances.
   * X = (instances, time steps per instance, channels)  
   * y =  (instances, label) # activity classification  
   * s =  (instances, sub) # subject number
   * ss_time = (instances, 2) # start and stop time of the window
* Clean and further transform the IR2 arrays as needed - note the transforms that can be applied here are train vs test dependent.   For example, the IR2 arrays in the training set may be dropped if multi-class or rebalanced, but those in the test set should not.
* Concatenate the processed IR2 arrays into the final returned train/validate/test arrays.

TWRistAR is small and easily downloadable so there is no option to used saved Intermediate Representations here as there is in some of the loaders for larger datasets.

Set interactive to true to run the Jupyter Notebook version.  Note most of the interactive calls are setup to test the functions, not process the entire dataset, to do that set interactive to false and run all so that main executes.   This notebook can be saved and run as a python file as well.

This video describes the code https://mediaflo.txstate.edu/Watch/e4_data_processing. (many updates have been made since this was recorded)


Acknowledgement to and a good example of the WISDM format being pre-processed is https://towardsdatascience.com/human-activity-recognition-har-tutorial-with-keras-and-core-ml-part-1-8c05e365dfa0  by Nils Ackermann.  


<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.

[Lee B. Hinkle](https://userweb.cs.txstate.edu/~lbh31/), Texas State University, [IMICS Lab](https://imics.wp.txstate.edu/)  
TODO:
* Time is off by 6 hrs due to time zone issues - adjusted in Excel/csv but would be good to show it in the correct time zone.
* The train and test groups for scripted activities are handled identically which is probably OK for TWristAR since it is balanced but it would be better to separate the big X, y, sub arrays out before dropping windows etc.
* Need to incorporate session numbers or just use the alternate .csv files where validation was 'fake' subs 11 and 22 which were just a few of the sessions from subjects 1 and 2.  This was done in the Semi-Supervised version of the loader for WISHWell but not integrated back into this version.

# Import Libraries
"""

import os
import shutil #https://docs.python.org/3/library/shutil.html
from shutil import unpack_archive # to unzip
import urllib.request # to get files from web w/o !wget

import time
from time import gmtime, strftime, localtime #for displaying Linux UTC timestamps in hh:mm:ss
from datetime import datetime, date

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder

def get_web_file(fname, url):
    """checks for local file, if none downloads from URL.    
    :return: nothing"""
    if (os.path.exists(fname)):
        print ("Local",fname, "found, skipping download")
    else:
        print("Downloading",fname, "from", url)
        urllib.request.urlretrieve(url, filename=fname)

"""# Load shared transform (xforms) functions and utils from IMICS Public Repo


"""

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
dataset_dir = my_dir # TWristAR zip file contains TWristAR directory
working_dir = os.path.join(my_dir,'TWristAR_temp') # temp dir for processing

if not os.path.exists(working_dir):
    os.makedirs(working_dir)
interactive = True # for exploring data and functions interactively
verbose = True

log_info = "" # a global to append dataset processing info

# dataset parameters
all_channel_list = ['accel_x', 'accel_y', 'accel_z','accel_ttl','bvp','eda','p_temp']
# frequency = 32 - unlike some of the other loaders this is hardcoded due to
# the unique sample freqencies that differ between the individual e4 sensors
xforms.time_steps = 96 # three seconds at 32Hz
xforms.stride = 32 # one second step for each sliding window
# The label_map_<dataset> contains a mapping from strings to ints for all
# possible labels in the entire dataset.   This allows for predictable conversion
# regardless of the slices.  I'm using 99 for 'unknown' which will be dropped
# to avoid the confusion of shifing by 1 place, zero indexed etc.
# Also this label map dict is setup to handle multi-labels but TWRristAR 
# has only a single activity label.
subj_alloc_dict = dict (train_subj = [1,2], valid_subj = [], test_subj = [3])
label_map_twristar = {"label":     {"Downstairs": 0, "Jogging": 1, "Sitting": 2,
                                "Standing": 3, "Upstairs": 4, "Walking": 5,
                                "Undefined": 99}}
scripted = True # TWristAR has two categories of data - scripted activities
                # and unscripted, set to false to get the unscripted data.
                # See example in bottom of this notebook.

interactive = False # don't run if interactive, automatically runs for .py version
verbose = False # to limit the called functions output

def get_TWristAR():
    """checks for local zipfile, if none downloads from zenodo repository
    after download will unzip the dataset into TWristAR directory.
    Assumes a global my_dir has been defined (default is my_dir = ".")
    :return: nothing"""
    zip_ffname = os.path.join(my_dir,'TWristAR.zip')
    if (os.path.exists(zip_ffname)):
        if verbose:
            print ("Local TWristAR.zip found, skipping download")
    else:
        print("Downloading TWristAR from Zenodo")
        urllib.request.urlretrieve("https://zenodo.org/record/5911808/files/TWristAR.zip", filename="TWristAR.zip")
    if (os.path.isdir(os.path.join(dataset_dir,'TWristAR'))):
        if verbose:
            print("Found existing TWristAR directory, skipping unzip")
        return
    else:
        print("Unzipping TWristAR file in", dataset_dir, "directory")
        if (os.path.exists(zip_ffname)):
            shutil.unpack_archive(zip_ffname,dataset_dir,'zip')
        else:
            print("Error: ", zip_ffname, " not found, exiting")
            return
if interactive:
    get_TWristAR()

def unzip_e4_file(zip_ffname):
    """checks for local copy, if none unzips the e4 zipfile in working_dir
    Note:  the files themselves do not contain subject info and there are
    multiple files e.g. ACC.csv, BVP,csv etc, in each zipfile.
    It is very important to further process the files with <fname>_labels.csv
    :param zip_ffname: the path and filename of the zip file
    :param working_dir: local (colab) directory where csv files will be placed
    :return: nothing"""
    if not os.path.exists(working_dir):
        print("Error working directory", working_dir, "not found, unzip_e4_file exiting")
        return
    if (os.path.exists(zip_ffname)):
        if verbose:
            print("Unzipping",zip_ffname, "in", working_dir)
        shutil.unpack_archive(zip_ffname,working_dir,'zip')
    else:
        print("Error: ", zip_ffname, " not found, exiting")
        return
if interactive:
    zip_ffname = os.path.join(my_dir,'TWristAR','sub1/1574621345_A01F11.zip')
    unzip_e4_file(zip_ffname)

def df_from_e4_csv (ffname,col_labels):
    """"reads e4 ACC, BVP, EDA, or TEMP(erature) csv files, uses start time and
    sample rate to create time indexed pandas dataframe with columns.  
    Note the other e4 files have different format and must be read seperately. 
    :param ffname:  full filename e.g./content/temp/ACC.csv
    :col_labels: list of colums in csv - varies by type ['accel_x','accel_y...]
    :returns df: time indexed dataframe"""

    df = pd.read_csv(ffname, header=None)
    start_time = df.iloc[0,0].astype('int64') # first line in e4 csv
    sample_freq = df.iloc[1,0].astype('int64') # second line in e4 csv
    df = df.drop(df.index[[0,1]]) # drop 1st two rows, index is now off by 2
    # Convert the index to datetime to allow for pandas resampling
    # The start_time from the e4 csv file is forced to int64 which represents the
    # number of nanoseconds since January 1, 1970, 00:00:00 (UTC)
    # This is tricky - if float representation the join function may not work
    # properly later since the indexes must match exactly.
    # UTC_time is computed for each row, then made into required datetime format
    # which is a int64 that pandas will accept as an index
    df['UTC_time'] = (df.index-2)/sample_freq + start_time
    end_time = df['UTC_time'].iloc[-1]
    if verbose:
        print(ffname, "Sample frequency = ", sample_freq, " Hz")
        #show time in day month format, assumes same timezone
        print("File start time = ", strftime("%a, %d %b %Y %H:%M:%S", localtime(start_time)))  
        print("File end time   = ",strftime("%a, %d %b %Y %H:%M:%S", localtime(end_time)))
    df['datetime'] = pd.to_datetime(df['UTC_time'], unit='s')
    df.set_index('datetime',inplace=True)
    df = df.drop('UTC_time', axis=1)
    df.columns = col_labels
    return df
if interactive:
    # Note: IBI.csv is the inter-beat interval, a calculated value with a 
    # different format.  HR.csv is also calculated from BVP but format is same.
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
    This method is e4 specific due to the way the accelerations is recorded
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

def get_ir1_from_e4_dir():
    """processes the four e4 sensor files in global working directory into a 
    single IR1 datetime indexed dataframe. Labeled columns are channels"""
    # Note: IBI.csv is the inter-beat interval, a calculated value with a 
    # different format.  HR.csv is also calculated from BVP but format is same.
    # TODO:  Should check directory for all four files and uniform start/stop
    # times.
    # TODO: Might be better to use a different interpolation.  See
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.interpolate.html
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
    if verbose:
        print("IR1 full dataframe shape",ir1_df.shape)
        #print(ir1_df.head(10))
    return ir1_df
if interactive:
    ir1_df = get_ir1_from_e4_dir()
    display(ir1_df.head(10))
    ir1_df.iloc[499:1999].plot(subplots=True, figsize=(20, 10)) # plot a few seconds

def show_e4_tag_time(tag_ffname):
    """utility prints time marks from e4 tags.csv to help with video sync 
    and labeling.   When this is run in colab it seems to be GMT regardless
    of timezone settings."
    :param tag_ffname: file to be processed e.g. /content/temp/tags.csv'
    :return: nothing"""
    df_temp = pd.read_csv(tag_ffname, header=None)
    df_temp.columns = ['UTC_time']
    print ("    UTC_time          Local Time")
    for index, row in df_temp.iterrows():
        print(index, row['UTC_time'],
            strftime("%a, %d %b %Y %H:%M:%S", localtime(row['UTC_time'])))
# https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
# link to string formats for date and time
if interactive:
    print('Tag info (button presses) from tags.csv')
    tag_ffname = working_dir + '/tags.csv'
    show_e4_tag_time(tag_ffname)

def label_df_from_csv (df, labels_ffname):
    """adds class label and subject number to the dataframe based on the
    contents of a .csv file containing time and label info.
    Example csv format (see e4_time_sync.xlsx to help build csv from video)
        start,finish,label,sub
        2019:11:24 18:49:51,2019:11:24 18:50:18,Upstairs,1
        2019:11:24 18:50:18,2019:11:24 18:50:45,Downstairs,1
    :param df : time indexed dataframe from df_from_e4_csv method
    :labels_ffname : csv file with metadata
    :return : a dataframe with label and subject columns added"""
    df_labels = pd.read_csv(labels_ffname)
    df_labels['start'] =  pd.to_datetime(df_labels['start'], format='%Y:%m:%d %H:%M:%S')
    df_labels['finish'] =  pd.to_datetime(df_labels['finish'], format='%Y:%m:%d %H:%M:%S')
    # quick check to make sure all subjects are the same - only 1 sub per csv
    if (not (df_labels['sub'].eq(df_labels['sub'].iloc[0]).all())):
        print('Warning: Multiple subjects detected in csv, unusual for e4 data.')
    df['label']='Undefined' # add column with safe value for labels
    df['sub'] = np.NaN
    for index, row in df_labels.iterrows():
        #print(row['start'], row['finish'],row['label'])
        df.loc[row['start']:row['finish'],'label'] = row['label']
        df.loc[row['start']:row['finish'],'sub'] = row['sub']
    return df
if interactive:
    labels_ffname = os.path.splitext(zip_ffname)[0] + '_labels.csv'
    print("Adding label and sub info from ",labels_ffname)
    ir1_df = label_df_from_csv(ir1_df, labels_ffname)
    display(ir1_df[5000:5005]) # head is meaningless since start is undefined
    #ir1_df['label'].value_counts()
    print ("Label Counts - # samples before sliding window")
    print (ir1_df['label'].value_counts())

def get_twristar_ir1_dict():
    """reads the TWRistAR dataset and converts each "session file" to an IR1
    dataframe.  The goal here is to capture and convert all raw data into
    a 2D dataframe of rows = datetime index of each sample, columns = {channels,
    label(s), subject_num}.  Additional methods may be used to drop channels,
    and convert the string labels to mapped ints prior to switch to ndarrays.
    Args:
    none but uses global scripted (boolean):
     True (default) returns scripted activity dataframes,
     False returns unscripted activity dataframes.
    Returns: a dict containing key = df_name and item = IR1 dataframes."""
    # A few notes - TWRristAR (or more specifically e4 wristband datafiles)
    # require a lot of processing, if trying to leverage from a more traditional
    # .csv file format see Gesture Phase version.
    if scripted:
        fn_list = ['sub1/1574621345_A01F11.zip',
                    'sub1/1574622389_A01F11.zip',
                    'sub1/1574624998_A01F11.zip',
                    'sub2/1633107019_A01F11.zip',
                    'sub2/1633108344_A01F11.zip',
                    'sub2/1633109744_A01F11.zip',
                    'sub3/1633704587_A01F11.zip',
                    'sub3/1633705664_A01F11.zip',
                    'sub3/1633711821_A01F11.zip']
    else:
        fn_list = ['sub1/1574625540_A01F11.zip',
                    'sub2/1633111849_A01F11.zip']
    get_TWristAR()
    ir1_df_dict = dict() # an empty dictionary
    for item in fn_list:
        zip_ffname = os.path.join(my_dir,'TWristAR',item)
        if verbose:
            print('Processing ', zip_ffname)
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        unzip_e4_file(zip_ffname)
        df = get_ir1_from_e4_dir()
        if verbose:
            print('Tag info (button presses) from tags.csv')
            tag_ffname = working_dir + '/tags.csv'
            show_e4_tag_time(tag_ffname)
        # Generate associated csv filename, forces the long numbered filenames to match
        labels_ffname = os.path.splitext(zip_ffname)[0] + '_labels.csv'
        df = label_df_from_csv (df, labels_ffname)
        df['label'].value_counts()
        if verbose:
            print ("Label Counts - # samples before sliding window\n",df['label'].value_counts())
        # tighten up the column types for space savings.
        # change to 32-bit, credit/ref https://stackoverflow.com/questions/69188132/how-to-convert-all-float64-columns-to-float32-in-pandas
        # Select columns with 'float64' dtype  
        float64_cols = list(df.select_dtypes(include='float64'))
        # The same code again calling the columns
        df[float64_cols] = df[float64_cols].astype('float32')
        # Seems better to explicitly type the other columns vs object.
        df['label']=df['label'].astype('category')
        df['sub']=df['sub'].astype('category') # this is before convert to int

        root_fname = (item.split('/')[1].split('.')[0]) # between / and .
        ir1_df_dict[root_fname]=df # key is root name in the file
    return ir1_df_dict
if interactive:
    verbose = False
    ir1_dict = get_twristar_ir1_dict()
    print('Scripted IR1 dataframes:',ir1_dict.keys())
    for df_name, df in ir1_dict.items():
        display(df.head())
        break # just want one
    scripted = False # get the free-form walk IR1s instead
    ir1_dict = get_twristar_ir1_dict()
    print('\nUnscripted IR1 dataframes:',ir1_dict.keys())
    for df_name, df in ir1_dict.items():
        display(df.head())
        break # just want one
    scripted = True
    verbose = True

"""# The dataset specific code to generate the dictionary of IR1 dataframes is complete.  Now use Shared Transforms to generate the final output arrays."""

def twristar_load_dataset(
    incl_val_group = False, # split train into train and validate
    keep_channel_list = ['accel_ttl'],
    one_hot_encode = False, # make y into multi-column one-hot, one for each activity
    suppress_warn = False # special case for stratified warning
    ):
    """Downloads the TWristAR dataset from Zenodo, processes the data, and
    returns arrays by separating into _train, _validate, and _test arrays for
    X and y based on split_sub dictionary."""
    global log_info
    log_info = "Generated by TWristAR_load_data.ipynb\n"
    today = date.today()
    log_info += today.strftime("%B %d, %Y") + "\n"
    log_info += "sub dict = " + str(subj_alloc_dict) + "\n"
    if scripted:  # this is a global variable in dataset params at top
        label_xform = 'drop' # for scripted activities used to train drop mixed
    else:
        label_xform = 'mode' # for unscripted assign mode label to every window 
    ir1_dict = get_twristar_ir1_dict()
    X, y, sub, ss_times, xys_info = xforms.get_ir3_from_dict(ir1_dict, 
                                                            label_map = label_map_twristar,
                                                            label_method = label_xform) 
    # Drop unwanted channels from X
    log_info += "Keeping channels" + str(keep_channel_list) + "\n"
    X = xforms.limit_channel_ir3(X, all_channel_list = all_channel_list, keep_channel_list = keep_channel_list)
    # write initial array info to log_info
    log_info += "Initial Arrays\n"
    log_info += utils.tabulate_numpy_arrays({'X':X,'y':y,'sub':sub,'ss_times':ss_times})+'\n'

    if (one_hot_encode):
        # tried to specify list to make sure all possible classes are encoded
        # label_list = list(label_map_twristar['label'].keys())
        # then pass categories=label_list but this does not work because the
        # list is longer than the classes due to the inclusion of undefined.
        # Note sparse was changed to sparse_output but that fails on my Mac
        enc = OneHotEncoder(categories='auto', sparse=False)
        y = enc.fit_transform(y)
        y=y.astype('uint8')
        # print(enc.categories_)
        log_info += "y has been one hot encoded" + str(enc.categories_) + '\n'

    sub_num = np.ravel(sub[ : , 0] ) # convert shape to (1047,)
    # this code is different from typical due to limited subjects,
    # all not test subjects data is placed into train which is then 
    # split using stratification - validation group is not sub independent
    train_index = np.nonzero(np.isin(sub_num, subj_alloc_dict['train_subj'] + 
                                        subj_alloc_dict['valid_subj']))
    x_train = X[train_index]
    y_train = y[train_index]
    if (incl_val_group):
        if not suppress_warn:
            print("Warning: Due to limited subjects the validation group is a stratified")
            print("90/10 split of the training group.  It is not subject independent.")
        # split training into training + validate using stratify - note that the
        # validation set is not subject independent (hard to achieve with limited
        # subjects).   The test set however is subject independent and as a result
        # will have much lower accuracy.  Another option is to tag a few of the
        # activities for inclusion in validation.  See
        # https://github.com/imics-lab/Semi-Supervised-HAR-e4-Wristband
        # https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html
        x_train, x_valid, y_train, y_valid = train_test_split(x_train, y_train, test_size=0.10, random_state=42, stratify=y_train)

    test_index = np.nonzero(np.isin(sub_num, subj_alloc_dict['test_subj']))
    x_test = X[test_index]
    y_test = y[test_index]

    if (incl_val_group):
        log_info += utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                       'x_valid': x_valid, 'y_valid': y_valid,
                                   'x_test': x_test, 'y_test': y_test})   
        return x_train, y_train, x_valid, y_valid, x_test, y_test
    else:
        log_info += utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                   'x_test': x_test, 'y_test': y_test})
        return x_train, y_train, x_test, y_test

"""# Main is setup to be a demo and bit of unit test."""

if __name__ == "__main__":
    verbose = False
    print("Get TWristAR using defaults - simple and easy!")
    x_train, y_train, x_test, y_test \
                             = twristar_load_dataset()
    print(utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                   'x_test': x_test, 'y_test': y_test}))
    print ('\n','-'*72)

    print("Get TWristAR with one-hot-encoded labels - dimension of y will be 6")
    x_train, y_train, x_test, y_test \
                             = twristar_load_dataset(one_hot_encode=True)
    print(utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                   'x_test': x_test, 'y_test': y_test}))
    print ("Sum of the columns, # of one-hot instances")
    print (y_train.sum(axis=0))
    y_labels = np.argmax(y_train, axis=-1) # undo one-hot encoding
    
    print("Back to integer encoded")
    unique, counts = np.unique(y_labels, return_counts=True)
    print (np.asarray((unique, counts)).T)

    print("Back to strings using xforms.get_ir2_y_string_labels and label_map")
    y_strings = xforms.get_ir2_y_string_labels(y_labels, label_map = label_map_twristar)
    unique, counts = np.unique(y_strings, return_counts=True)
    print (np.asarray((unique, counts)).T)
    print ('\n','-'*72)

    print("Get TWristAR with validation group, info file, and four channels\n")
    x_train, y_train, x_valid, y_valid, x_test, y_test \
                             = twristar_load_dataset(
                                 incl_val_group = True,
                                 keep_channel_list = ['accel_ttl','bvp',
                                                      'eda', 'p_temp'])
    print(utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                       'x_valid': x_valid, 'y_valid': y_valid,
                                   'x_test': x_test, 'y_test': y_test}))

    print("\n----------- Contents of log_info ---------------")
    print(log_info)
    print("\n------------- End of log_info -----------------")
    print("Get TWristAR with validation group, no warn, and bvp only\n")
    x_train, y_train, x_valid, y_valid, x_test, y_test \
                             = twristar_load_dataset(
                                 incl_val_group = True,
                                 keep_channel_list = ['bvp'],
                                 suppress_warn = True)
    print("This is a no output config - silent execution")
    print(utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                       'x_valid': x_valid, 'y_valid': y_valid,
                                   'x_test': x_test, 'y_test': y_test}))
    print ('\n','-'*72)
    print("Get TWristAR with validation group, and accel only\n")
    x_train, y_train, x_valid, y_valid, x_test, y_test \
                             = twristar_load_dataset(
                                 incl_val_group = True,
                                 keep_channel_list = ['accel_x', 'accel_y', 'accel_z', 'accel_ttl'],
                                 suppress_warn = True)
    print(utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                       'x_valid': x_valid, 'y_valid': y_valid,
                                   'x_test': x_test, 'y_test': y_test}))
    print("\n----------- Contents of log_info ---------------")
    print(log_info)
    print("\n------------- End of log_info -----------------")
    # Test the ability to get and process the unscripted free-form walks
    # These are generally treated as unlabeled sequences for our labeling work
    # It is setup so sub 1 walk is the train array, sub2 is the test array.
    # And they are in fact labeled for final validation.
    scripted = False # this is a global variable assigned at begining
    print ('\n','-'*72)
    print("Get TWristAR Free-Form Walks - Test = Sub1, Train = Sub2\n")
    subj_alloc_dict = dict(train_subj = [1], valid_subj = [], test_subj = [2])
    x_train, y_train, x_test, y_test \
                             = twristar_load_dataset(
                                 keep_channel_list = ['accel_x', 'accel_y', 'accel_z', 'accel_ttl'],
                                 suppress_warn = True)
    print(utils.tabulate_numpy_arrays({'x_train': x_train, 'y_train': y_train,
                                   'x_test': x_test, 'y_test': y_test}))
    scripted = True   # put it back where you found it!