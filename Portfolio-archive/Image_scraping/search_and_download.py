from fetch_image_urls import fetch_image_urls
from persist_image import persist_image
import os
from selenium import webdriver
from sku_list import sku_df
import pandas as pd
import numpy as np

def search_and_download(search_term:str,driver_path:str,target_path='./images',number_images=5):
    target_folder = os.path.join(target_path,'_'.join(search_term.lower().split(' ')))#.replace(' ', '_').lower()))#.lower()).split(' '))

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    with webdriver.Chrome(executable_path=driver_path) as wd:
        res = fetch_image_urls(search_term, number_images, wd=wd, sleep_between_interactions=0.5)
        
    i=0
    for elem in res:
        persist_image(target_folder,elem)
        if i<3:
        	i += 1
        else:
        	return()

	
sku_df = pd.read_csv("sku.csv", header=None )
sku_df.columns = ['Names']
#sku_df_index = sku_df.set_index(,drop=True, append=False, inplace=False, verify_integrity=False)
#print(sku_df.head())
#print(sku_df.iloc[:,0])
# Create an empty list 
sku_df_new = sku_df.drop([0])
sku_list = sku_df_new['Names'].tolist()
#print(sku_df.head())

for k in sku_list:
	search_and_download(k, 'chromedriver')
	
