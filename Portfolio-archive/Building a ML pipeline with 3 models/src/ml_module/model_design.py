#!/usr/bin/env python
# coding: utf-8

# In[45]:

from sklearn.model_selection import KFold, cross_val_score
from sklearn.linear_model import LogisticRegression
import pandas as pd
import numpy as np
from category_encoders import TargetEncoder
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.naive_bayes import GaussianNB
#from data_processing import x_scaled

def model_results(x_train, x_test, y_train, y_test, x_scaled, y):
    
    # Create a Random Forest Classifier with specified criterion
    rf_class = RandomForestClassifier()

    #create a dictionary to score the accuracy scores.
    accuracies = {}

    #Random forest classifier:
    rf_model = RandomForestClassifier().fit(x_train, y_train.values.ravel())
    rf_predictions = rf_model.predict(x_test)
    accuracies['rf'] = accuracy_score(y_test, rf_predictions)
    print (accuracies)

    #setting up a parameter grid to see if we can improve the result
    param_grid = {'max_depth':[2,4,6,8,10], 'max_features':['auto', 'sqrt']}

    #Creating a GridSearchCV object
    grid_rf_class = GridSearchCV(
        estimator = rf_class,
        param_grid=param_grid,
        scoring='roc_auc',
        n_jobs=4,
        cv=5, 
        refit=True, return_train_score=True)
    print(grid_rf_class)

    # Fit CV to the training set, see if the result changes.
    grid_rf_class.fit(x_train, y_train.values.ravel())

    # Predict the labels of the test set: y_pred
    y_pred = grid_rf_class.predict(x_test)

    # Compute and print metrics
    print("Accuracy: {}\n\n".format(grid_rf_class.score(x_test, y_test)))
    print("classification report \n\n", classification_report(y_test, y_pred))
    print("Tuned Model Parameters: \n\n {}".format(grid_rf_class.best_params_))
    print ("Random forest COMPLETE! \n\n")
    
    ##
    ##
    #Now, let's do Logistic Regression
    
    from sklearn.linear_model import LogisticRegression
    lr_model = LogisticRegression()
    lr_model.fit(x_train, y_train)
    lr_model.score(x_test,y_test)
    
    #hyperparameter tuning
    # Define the grid of values for tol and max_iter
    tol = [0.01, 0.001, 0.0001]
    max_iter = [100, 150, 200]

    # Create a dictionary where tol and max_iter are keys and the lists of their values are corresponding values
    param_grid = dict(tol=tol, max_iter = max_iter)
    
    # Instantiate GridSearchCV with the required parameters
    grid_model = GridSearchCV(estimator=lr_model, param_grid=param_grid, cv=5)

    # Fit data to grid_model
    grid_model_result = grid_model.fit(x_scaled, y.values.ravel())

    # Summarize results
    best_score, best_params = grid_model_result.best_score_, grid_model_result.best_params_ 
    print("Best: %f using %s" % (best_score, best_params))
    print ("Logistic Regression COMPLETE! \n\n")
    
    ##
    ##
    #Now, let's do Naive Bayes
    from sklearn.naive_bayes import GaussianNB
    
    nb_model = GaussianNB()
    predict_train = nb_model.fit(x_train, y_train.values.ravel()).predict(x_train)
    
    predict_test = nb_model.predict(x_test)
    #Accuracy scores
    accuracy_train = accuracy_score(y_train,predict_train)
    accuracy_test = accuracy_score(y_test,predict_test)
    print ("accuracy_score on the train dataset : ", accuracy_train)
    print ("accuracy_score on the test dataset : ", accuracy_test)
    
    #Hyperparameter tuning to improve accuracy
    from sklearn.model_selection import RepeatedStratifiedKFold
    cv_method = RepeatedStratifiedKFold(n_splits=5,  n_repeats=3, random_state=123)

    from sklearn.preprocessing import PowerTransformer
    params_NB = {'var_smoothing': np.logspace(0,-9, num=100)}

    gs_NB = GridSearchCV(estimator=nb_model, param_grid=params_NB, cv=cv_method,verbose=1,scoring='accuracy')
    Data_transformed = PowerTransformer().fit_transform(x_test)
    gs_NB.fit(Data_transformed, y_test.values.ravel());
    
    results_NB = pd.DataFrame(gs_NB.cv_results_['params'])
    results_NB['test_score'] = gs_NB.cv_results_['mean_test_score']
    # predict the target on the test dataset
    predict_test = gs_NB.predict(Data_transformed)
    # Accuracy Score on test dataset
    accuracy_test_nb = accuracy_score(y_test,predict_test)
    print('accuracy_score on test dataset : ', accuracy_test_nb)
    print ("Naive Bayes COMPLETE! \n\n")
    return best_score, accuracy_test_nb, (grid_rf_class.score(x_test, y_test))


