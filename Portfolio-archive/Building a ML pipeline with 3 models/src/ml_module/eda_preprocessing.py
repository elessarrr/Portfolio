#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import sqlite3 as sql


# In[ ]:


def eda_preprocessing():
    database = "data/survive.db"
    connection =sql.connect(database)
    query = '''SELECT * FROM survive'''
    df = pd.read_sql_query(query,connection)
    
    #I was able to run the script as is on jupyter notebook, but my Macbook is throwing errors. 
    #I'm troubleshooting the root cause, but to stay in the deadline, I was debugging using the dataframe in xlsx. 
    #In case you need to, kindly use the code below. I removed the xlsx file from the submission because of the clear instruction not to include the dataset.
    
    #df = pd.read_excel('df.xlsx', index_col=None)
    #df = df.iloc[: , 1:]


    print('extracting data...')
    df.head() 
    df.shape #ensure that the data is properly loaded    
    df = df[df['Age']>0] # remove rows where Age is negative for some reason
    
    #fix values that are incorrect
    df["Survive"].replace({"No": "0", "Yes": "1"}, inplace=True)
    df["Smoke"].replace({"NO": "No", "YES": "Yes"}, inplace=True)
    df["Ejection Fraction"].replace({"N": "Normal", "L": "Low"}, inplace=True)
    
    #filling the empty creatinine values with the median in the column.
    df['Creatinine']=df['Creatinine'].fillna(df['Creatinine'].median())
    
    df.rename(columns={'Survive': 'Target'},inplace=True)

    # Print out the first 2 rows just to check
    df.head(2)
    print ("ready for the next step!")
    return df   

