#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd

from ml_module.eda_preprocessing import eda_preprocessing
from ml_module.data_processing import split_data
from ml_module.model_design import model_results

dataset = eda_preprocessing() #this return the survive dataset in a dataframe, cleaned and ready for machine learning.
#print(dataset)
x_train, x_test, y_train, y_test, x_scaled, y = split_data(dataset) # train test split of abovementioned dataset. We will reuse this split for all 3 models.
#print(y_train)

#scores for classification

best_score_lr, best_score_nb, best_score_rf = model_results(x_train,x_test,y_train,y_test, x_scaled, y)

#Printing results onto df
results_df = pd.DataFrame(np.array([["Logistic regression best score after hyper parameter tuning", best_score_lr], ["Naive Bayes method best score after tuning", best_score_nb],["Random Forest Classifier", best_score_rf]]),
                   columns=['Model', 'Score'])

results_df.to_csv(r'src/results/model_score.csv', index=False)