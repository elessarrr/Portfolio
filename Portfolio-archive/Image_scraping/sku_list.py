# Import libraries

import pandas as pd
import numpy as np
from sklearn.manifold import TSNE

# Load the data
sku_df = pd.read_csv("sku.csv", header=None)
sku_df.columns = ['Names']
#sku_df_index = sku_df.set_index(,drop=True, append=False, inplace=False, verify_integrity=False)
#print(sku_df.head())
#print(sku_df.iloc[:,0])
# Create an empty list 
sku_df_new = sku_df.drop([0])
sku_list = sku_df_new['Names'].tolist()
print (type(sku_list))
print (sku_list)

