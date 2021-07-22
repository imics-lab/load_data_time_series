# load_data_time_series
Generate numpy arrays for classification tasks from public datasets containing sensor data.

The intention of this work is to allow quick testing of mulitple time-series datasets when evaluating new models.   Our [research](https://imics.wp.txstate.edu/) is in the area of biosignals; time series data may include motion (accel/gyro), ECG (heart electrical), EEG (brain electrical), EOG (eye movement), EMG (muscle activation), EDA (skin conductance) and others.   The common attribute is that all of these signals are sampled over time typically in frequencies from 1 to 256 samples per second.

For the quickest dive in, the [HAR/load\_dataset\_demo.ipynb](HAR/load\_dataset\_demo.ipynb) is a good starting point.

Each of datasets are converted into numpy files that can be used to train/validate a model.   The goal is to make this as simple as the MNIST load_data function in [Keras](https://keras.io/api/datasets/mnist/#load\_data-function) or Tensorflow.  Since each dataset is provided in a different format there are multiple &lt;dataset&gt;\_load\_dataset.ipynb files currently.  These files can be run as Jupyter notebooks or the .py version can be used (see the demo for examples).   The initial three HAR datasets were chosen in part due to popularity and also because they represent a range of pre-processing:  MobiAct is mostly raw data, UniMiB has segmented data, and UCI HAR provides a pre-defined train/test split.
  
As I worked on the load_dataset code I realized that it would be more efficient to get to a common interim representation first.   This resulted in the two &lt;dataset&gt;\_get\_X\_y\_sub.ipynb notebooks which are intended to be run interactively with the resulting X, y, sub(ject) numpy arrays stored for use elsewhere.   I have some ideas on how to standardize this further but want to try a few non-HAR data sets before committing to anything.

In addition to supporting general research needs an analysis was done of the impact of subject allocation into train/test/validate groups for this paper.
>Hinkle L.B., Metsis V. (2021) Model Evaluation Approaches for Human Activity Recognition from Time-Series Data. In: Tucker A., Henriques Abreu P., Cardoso J., Pereira Rodrigues P., Riaño D. (eds) Artificial Intelligence in Medicine. AIME 2021. Lecture Notes in Computer Science, vol 12721. Springer, Cham. [https://doi.org/10.1007/978-3-030-77211-6_23](https://doi.org/10.1007/978-3-030-77211-6_23)

Hope this is useful and my thanks goes out to the researchers who have spent the time and effort to collect the data and published the datasets.

[Lee](https://userweb.cs.txstate.edu/~lbh31/)
