import googleapiclient.discovery as gapi
import pprint
import math as m
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# API information
api_service_name = "youtube"
api_version = "v3"
# API key
DEVELOPER_KEY = "AIzaSyCJswyCUfpL08hpDp-qJGaIf3cZj9Ghw3U"
# API client
youtube = gapi.build(
    api_service_name, api_version, developerKey=DEVELOPER_KEY
)
# 'request' variable is the only thing we must change depending on what we want

# Request body
request1 = youtube.channels().list(
    part="id,snippet",
    forUsername="derpingaround1",
    fields="items(id,snippet(title,description))"
)
# Request execution
response1 = request1.execute()

# so far pulled my channel's ID
channel_ID = response1['items'][0]['id']
print(f"Channel ID is: {channel_ID}")

# Use channel ID to find who they are subscribed to
ptoken = ""
maxresults = 50
# first make a request, and from it extract page info to know how many more requests needed
# to get the full list
request2 = youtube.subscriptions().list(
    part="id,snippet",
    channelId=channel_ID,
    maxResults=maxresults,
    pageToken=ptoken,
    fields="items(id,snippet(title,resourceId(channelId))),nextPageToken,pageInfo"
)
response2 = request2.execute()
# make a list
channelsdict = {}
for item in response2['items']:
    channelsdict[item['snippet']['title']] = item['snippet']['resourceId']['channelId']


totalresults = response2['pageInfo']['totalResults']
print(f"Total results: {totalresults}")
totalpages = m.ceil(totalresults / maxresults)
print(f"Total number of requests needed: {totalpages}")
# if this value is greater than 1, we need to do more requests
if totalpages > 1:
    i = 1
    while i < 3: 
        ptoken = response2['nextPageToken']
        request2 = youtube.subscriptions().list(
            part="id,snippet",
            channelId=channel_ID,
            maxResults=maxresults,
            pageToken=ptoken,
            fields="items(id,snippet(title,resourceId(channelId))),nextPageToken"
        )
        response2 = request2.execute()
        for item in response2['items']:
            channelsdict[item['snippet']['title']] = item['snippet']['resourceId']['channelId']
        print(f"loop {i+1}")
        i += 1

# pprint.pprint(channelsdict)

# list of channel names
channelnames = list(channelsdict.keys())

# test the topicDetails resource
# print(f"Print topicDetails for channel: {channelnames[1]} with ID: {channelsdict[channelnames[1]]}")
# request3 = youtube.channels().list(
#     part="contentDetails,id,statistics,topicDetails",
#     id=[channelsdict[channelnames[1]]],
#     fields="items(topicDetails(topicCategories))"
# )
# response3 = request3.execute()
# pprint.pprint(response3)

# next use the above block (w/ username instead) to make a pandas df of the topic categories from all channels I follow
# df = pd.DataFrame()
# for channel in channelnames:

topics = []
for channelname in channelnames:
    request3 = youtube.channels().list(
        part="topicDetails",
        forUsername=channelname,
        fields="items(topicDetails(topicCategories))"
    )
    response3 = request3.execute()

    categorieslist = []
    if bool(response3):
        if bool(response3['items'][0]):
            categorieslist = response3['items'][0]['topicDetails']['topicCategories']
            categorieslist = [x.split('/')[-1] for x in categorieslist] # take the categories from the wiki links
    topics.append(categorieslist)

data = {'channels':channelnames, 'topics':topics}

df = pd.DataFrame(data=data)

df = df.join(df.topics.str.join('|').str.get_dummies(sep='|'))

freqs = np.array(df.iloc[:,2:]).sum(axis=0)
plt.bar(x=df.columns[2:], height=freqs)
plt.xticks(rotation=90)
plt.show()