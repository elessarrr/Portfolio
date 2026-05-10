#!/usr/bin/env python
# coding: utf-8

# # Let's process the data!

# In[ ]:


import pandas as pd
import numpy as np
from category_encoders import TargetEncoder
from sklearn.model_selection import train_test_split

def split_data(df):
    #first, let's encode the categorical variables, hereby noted as 'non_num_features' because they have no numbers.
    print('loading train test split...')
    non_num_features = ['Gender', 'Smoke', 'Diabetes','Ejection Fraction','Favorite color']
    num_features = ['Age', 'Sodium', 'Creatinine', 'Platelets', 'Creatine phosphokinase', 'Blood Pressure', 'Hemoglobin', 
                        'Height', 'Weight']

    non_num_features = pd.get_dummies(df[non_num_features])
    encoder = TargetEncoder()
    num_features = encoder.fit_transform(df[num_features], df['Target'])

    y = df[["Target"]]

    df_temp2 = pd.concat([non_num_features, num_features], axis=1)
    df_temp = pd.concat([y,df_temp2],axis=1)
    x = df_temp.loc[:, df_temp.columns != 'Target']
    print ("complete")
    
    #Step 2 - Let's scale feature data since some columns like Platelets are orders of magnitude larger than the rest, and will skew results since most ML models use distance to some extent. While there are a variety of scalers and normalisation techniques, let's use MinMaxScaler for this since it's straightforward and quick.
    
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    x_scaled = pd.DataFrame(scaler.fit_transform(x), columns = x.columns)
    x_scaled
    
    #now, let's do train_test_split!
    x_train, x_test, y_train, y_test = train_test_split(x_scaled, y , train_size = 0.7, random_state =  42)
    
    print('at this point we complete splitting of dataset into train and test sets. Since we were not given direction, I have elected to use 70/30 split which is conventionally common' )
    
    #for a quick sense check
    print ("x_train shape is ", x_train.shape)
    print ("y_train shape is ", y_train.shape)
    print ("x_test shape is ", x_test.shape)
    print ("y_test shape is ", y_test.shape)
    
    return x_train, x_test, y_train, y_test, x_scaled, y

