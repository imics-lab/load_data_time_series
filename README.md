## Time Series Classification Dataloaders

A comprehensive collection of preprocessed time-series datasets for classification tasks, designed to facilitate rapid model evaluation and research across multiple domains including human activity recognition (HAR), biosignals (EEG, ECG, EMG), traffic analysis, financial data, and astronomical observations.

## Overview

This repository provides standardized numpy arrays from public datasets containing sensor and time-series data. The primary goal is to make loading time-series datasets as simple as the MNIST `load_data()` function in Keras, TensorFlow and pyTorch enabling researchers to quickly test multiple datasets when evaluating new models.

Our research focuses on biosignals analysis, including motion (accelerometer/gyroscope), ECG (cardiac electrical activity), EEG (brain electrical activity), EOG (eye movement), EMG (muscle activation), and EDA (skin conductance). These signals are typically sampled at frequencies ranging from 1 to 256 samples per second.

## Datasets

This repository includes diverse time-series datasets across multiple domains:

### Human Activity Recognition (HAR)

#### UniMiB-SHAR
- **Train Size**: 4,601 | **Validation Size**: 1,454 | **Test Size**: 1,524
- **Length**: 151 time steps | **Classes**: 9
- **Description**: Accelerometer-based human activity recognition dataset with segmented data. Contains training, validation, and test splits for comprehensive model evaluation.

#### RacketSports
- **Train Size**: 151 | **Test Size**: 152
- **Length**: 30 time steps | **Classes**: 4
- **Description**: Movement data captured during racket sports activities including tennis and badminton.

### Biosignals (EEG/ECG)

#### Sleep
- **Train Size**: 478,785 | **Test Size**: 90,315
- **Length**: 178 time steps | **Classes**: 5
- **Description**: EEG signals for classifying five different sleep stages, providing a large-scale dataset for sleep stage classification research.

#### SelfRegulationSCP1
- **Train Size**: 268 | **Test Size**: 293
- **Length**: 896 time steps | **Classes**: 2
- **Description**: EEG signals related to self-regulation through slow cortical potentials (SCPs) for binary classification tasks.

#### SelfRegulationSCP2
- **Train Size**: 200 | **Test Size**: 180
- **Length**: 1,152 time steps | **Classes**: 2
- **Description**: Extended EEG dataset for self-regulation analysis with longer time series compared to SCP1.

#### FaceDetection
- **Train Size**: 5,890 | **Test Size**: 3,524
- **Length**: 62 time steps | **Classes**: 2
- **Description**: EEG signals recorded during face detection tasks, classifying whether a face is recognized or not.

### Audio

#### JapaneseVowels
- **Train Size**: 270 | **Test Size**: 370
- **Length**: 29 time steps | **Classes**: 9
- **Description**: Audio recordings of nine Japanese male speakers pronouncing vowels 'a' and 'e', preprocessed for time-series classification.

### Device and Sensor Data

#### ElectricDevices
- **Train Size**: 8,926 | **Test Size**: 7,711
- **Length**: 96 time steps | **Classes**: 7
- **Description**: Electrical consumption signatures of household devices for device-type classification.

#### MelbournePedestrian
- **Train Size**: 1,194 | **Test Size**: 2,439
- **Length**: 24 time steps | **Classes**: 10
- **Description**: Sensor data capturing pedestrian movement patterns in Melbourne with hourly aggregated flows.

### Financial Data

#### SharePriceIncrease
- **Train Size**: 965 | **Test Size**: 965
- **Length**: 60 time steps | **Classes**: 2
- **Description**: Daily share price movements for predicting whether a company's stock price will increase, useful for binary classification in financial forecasting.

### Astronomical Data

#### LSST (Large Synoptic Survey Telescope)
- **Train Size**: 2,459 | **Test Size**: 2,466
- **Length**: 36 time steps | **Classes**: 14
- **Description**: Light curve time-series data from astronomical observations for classifying 14 different types of celestial objects.

## Data Processing Pipeline

Each dataset undergoes a standardized preprocessing pipeline:

1. **Data Loading**: Datasets are loaded from `.arff` or `.ts` files using `scipy.io` and custom parsers
2. **Feature Extraction**: Separation of target labels from feature columns
3. **Normalization**: Standardization using `StandardScaler` for consistent feature scaling
4. **Reshaping**: Conversion to 3D format (samples × time steps × dimensions) for deep learning models
5. **Train/Validation/Test Splitting**: Appropriate data partitioning for model evaluation
6. **Tensor Conversion**: Transformation to PyTorch tensors for neural network training
7. **Batching**: Efficient data loading through `DataLoader` utilities

## Repository Structure

The repository contains multiple `<dataset>_load_dataset.ipynb` notebooks, each handling a specific dataset's unique format. These notebooks can be run interactively in Jupyter or executed as Python scripts (`.py` versions available).

For improved efficiency, `<dataset>_get_X_y_sub.ipynb` notebooks create intermediate representations, storing X (features), y (labels), and subject information as numpy arrays for downstream use.

## Dataset Selection Rationale

The initial HAR datasets were chosen to represent a spectrum of preprocessing approaches:
- **MobiAct**: Mostly raw sensor data
- **UniMiB-SHAR**: Pre-segmented data
- **UCI HAR**: Pre-defined train/test splits

This diversity ensures the repository supports various research methodologies and preprocessing preferences.

## Downloading Datasets

### UCR/UEA Time Series Classification Archive
Most datasets can be downloaded from:
[https://timeseriesclassification.com/dataset.php](https://timeseriesclassification.com/dataset.php)

### Repository-Specific Datasets
- **UniMiB-SHAR**: Available in the `UniMiB-SHAR` folder
- **Leotta_2021**: Available in the `Leotta_2021` folder

## Installation

Install required dependencies:

```bash
pip install numpy pandas scikit-learn scipy torch
```

## Usage Example

```python
# Load a dataset (example with UCI HAR)
from load_dataset import load_uci_har

X_train, y_train, X_test, y_test = load_uci_har()

# Use with your model
model.fit(X_train, y_train)
predictions = model.predict(X_test)
```

## Research and Citations

This repository has been used in multiple research publications for benchmarking and evaluating time-series classification models. If you use these datasets in your research, please consider citing the relevant papers:

### Publications Using This Repository

**Model Evaluation for Time Series Classification:**
> Hinkle L.B., Metsis V. (2021) Model Evaluation Approaches for Human Activity Recognition from Time-Series Data. In: Tucker A., Henriques Abreu P., Cardoso J., Pereira Rodrigues P., Riaño D. (eds) Artificial Intelligence in Medicine. AIME 2021. Lecture Notes in Computer Science, vol 12721. Springer, Cham.  
> [https://doi.org/10.1007/978-3-030-77211-6_23](https://doi.org/10.1007/978-3-030-77211-6_23)

**Positional Encoding Survey in time series transformer:**
> Irani H., Metsis V. (2025) Positional Encoding in Transformer-Based Time Series Models: A Survey. arXiv preprint arXiv:2502.12370.  
> [https://arxiv.org/abs/2502.12370](https://arxiv.org/abs/2502.12370)

**Time Series Embedding Methods for Classification:**
> Irani, H., Ghahremani, Y., Kermani, A., & Metsis, V. (2025). Time Series Embedding Methods for Classification Tasks: A Review. Expert Systems, 42(11), e70148. DOI: 10.1111/exsy.70148  
> [https://onlinelibrary.wiley.com/doi/full/10.1111/exsy.70148](https://onlinelibrary.wiley.com/doi/full/10.1111/exsy.70148)

These papers demonstrate the utility of this repository for:
- Evaluating subject allocation strategies in train/test splits
- Benchmarking positional encoding methods for transformer-based time series models
- Comparing classification approaches across diverse time-series domains
- Testing model generalization and performance across multiple datasets

## Contributing

Contributions are welcome! If you have additional datasets or improvements to the preprocessing pipeline, please submit a pull request.

## Acknowledgments

Special thanks to the researchers who collected and published these datasets, making this comparative research possible.

## Contact

[Lee Hinkle](https://userweb.cs.txstate.edu/~lbh31/)  
[Habib irani](https://userweb.cs.txstate.edu/~vux11/) 
[IMICS Research Group](https://imics-lab.github.io//)

## License

Please refer to individual dataset licenses and cite original dataset creators when using these datasets in publications.