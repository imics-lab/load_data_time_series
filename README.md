# load_data_time_series
Generate numpy arrays for classification tasks from public datasets

The intention of this work is to allow quick testing of time-series data when checking classifiers.   Our research is in the area of biosignals; time series data may include motion (accel/gyro), EKG, EEG, EOG (eye movement), EMG (muscle activation), EDA (skin conductance) and others.   The common attribute is that all of these signals are sampled over time.

For the quickest dive in, the HAR/load_dataset_demp.ipynb is a good starting point.

Each of the three Human Activity Recognition (HAR) datasets are converted into numpy files and read into a classifier.   The goal is to make this as simple as the MNIST import in Keras or Tensorflow.  Since each dataset is provided in a different format there are three <dataset>_load_dataset.ipynb files currently.  These files can be run in Jupyter or the .py version can be used (see the demo for examples).   These three datasets were chosen in part due to popularity and also because they represent a range of pre-processing:  MobiAct is mostly raw data, UniMiB has segmented data, and UCI HAR provides a pre-defined train/test split.
  
After working on the load_dataset code I realized that it would be better to get to a common interim representation.   This resulted in the two <dataset>_get_X_y_sub.ipynb notebooks which are intended to be run interactively with the resulting X, y, sub(ject) numpy arrays stored for use elsewhere.   I have some ideas on how to standardize this further but want to try a few non-HAR data sets before committing to anything.

In addition to supporting general research needs and analysis was done of the impact of subject allocation into train/test/validate groups which will be presented as a short paper "Model Evaluation Approaches for Human Activity Recognition from Time-Series Data" at the AIME2021 conference.   I'll add updates as the conference publications are available.

Hope this is useful and my thanks goes out to the researchers who collected and provided the data.

Lee
