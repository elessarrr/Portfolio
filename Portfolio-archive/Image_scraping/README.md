# Examples
Examples of work done

Image scraping a list of items, in Google Image search. BTW google will ban you for doing this - I did it more to see how it could work, but definitely don't run this large scale (or at all to be frank).

This is one of the earlier projects I did in my journey to self learn, which explains the bulky/wasteful code. Anyway I will upload as is more for myself to remember.

'sku.csv' is just an example of products you might have. You can make the list bigger or smaller and change it out for the name of the products you wish to search for.
'sku_list.py' is a simple function to read .csv files into a dataframe. You can actually include this in the main function.
'fetch_image_urls.py' is the first step to get images, where the default url is google's image search, and we look for thumbnails. You can also configure variables for how many pictures you want to pull. Correct content is found by searching within the CSS code for a specific css selector object; in case this changes in the future, you can change this part of the code too to adapt.
'persist_image.py' is the second step where once the image has been located, we pull the content, convert it to  the desired format and filename, and save it to the target folder.
'search_and_download.py' ties everything together and is the main function you'll need to call.


'
