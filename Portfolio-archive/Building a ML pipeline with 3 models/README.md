Thanks for taking the time to review my submission.

## Personal particulars


## Overview of the submitted folder and the folder structure:

.
├── README.md
├── __init__.py
├── data
│   └── survive.db
├── eda.ipynb
├── requirements.txt
├── run.sh
└── src
    ├── _init_.py
    ├── df.xlsx #removed
    ├── ml_module
    │	 ├── __pycache__
    │	 ├── _init_.py
    │	 ├── data_processing.py
    │	 ├── eda_preprocessing.py
    │	 └── model_design.py
    ├── requirements.txt
    ├── results
    │	 └── model_score.csv
    └── run.py

## Instructions:

### Installing dependencies
Paste the following command on your bash terminal to download dependencies:

```sh
pip install -r requirements.txt
```
### Running the Machine Learning Pipeline
Past the followin command on your bash terminal to grant permission to execute the 'run.sh' file
```sh
chmod +x run.sh
```
Paste the following command on the bash terminal to run the machine learning programme
```sh
./run.sh
```
### Reading the results
Please navigate to the folder src/results and open the file 'model_score.csv' to see a quick summary of the models employed and the best scores they were able to achieve for predicting survivors from the given dataset.



