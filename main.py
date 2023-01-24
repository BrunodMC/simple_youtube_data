import math as m
import base64
import io
import json
import typing

from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import HTMLResponse
import googleapiclient.discovery as gapi
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('AGG')
import matplotlib.pyplot as plt


### youtube API setup:
# API information
api_service_name = "youtube"
api_version = "v3"
# API key
DEVELOPER_KEY = "AIzaSyCJswyCUfpL08hpDp-qJGaIf3cZj9Ghw3U"
# API client
youtube = gapi.build(
    api_service_name, api_version, developerKey=DEVELOPER_KEY
)


# api setup:
app = FastAPI()

class PrettyJSONResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
        ).encode("utf-8")


@app.get("/")
def read_root() -> HTMLResponse:
    html_content = f"""
    <html>
        <head>
            <title>Root</title>
        </head>
        <body>
            <h1>Server is working.</h1>
        </body>
    </html>"""
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/{channel_name}", response_class=PrettyJSONResponse)
def read_channelstats(channel_name: str):
    req1 = youtube.channels().list(
        part="id",
        forUsername=channel_name,
        fields="items(id)"
    )
    resp1 = req1.execute()
    if not resp1:
        raise HTTPException(status_code=404, detail="Channel does not exist.")
    
    subsdict = find_subbed_channels(resp1['items'][0]['id'])
    output = {'chosenChannel':channel_name, 'subbedTo':subsdict}
    return output


@app.get("/{channel_name}/topics", response_class=PrettyJSONResponse)
def read_channeltopics(channel_name:str):
    req1 = youtube.channels().list(
        part="id",
        forUsername=channel_name,
        fields="items(id)"
    )
    resp1 = req1.execute()
    if not resp1:
        raise HTTPException(status_code=404, detail="Channel does not exist.")
    
    subsdict = find_subbed_channels(resp1['items'][0]['id'])

    topics = []
    for channel in subsdict['subbedChannels']:
        topics.append(find_channel_topics(channel))
    
    data = {'channels':subsdict['subbedChannels'], 'topics':topics}
    df = pd.DataFrame(data=data)
    # onehot the dataframe
    df = df.join(df.topics.str.join('|').str.get_dummies(sep='|'))
    # sum across columns to get bar plot data
    freqs = np.array(df.iloc[:, 2:]).sum(axis=0)
    plt.bar(x=df.columns[2:], height=freqs)
    plt.xticks(rotation=90)
    
    # save figure into buffered stream
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', bbox_inches='tight')
    plt.close()

    str_img_buf = base64.b64encode(img_buf.getvalue()).decode()

    totalempty = df.topics.apply(lambda x: 1 if len(x) == 0 else 0).sum()

    html_content = f"""
    <html>
        <head>
            <title>{channel_name}'s topics</title>
        </head>
        <body>
            <h1>Data:</h1>
            <p>{channel_name} is subbed to {subsdict['totalSubs']} channels.</p>
            <p>{totalempty} of those channels have no topics assigned to them.</p>
            <p>Frequency distribution of different topics:</p>
            <img src='data:image/png;base64,{str_img_buf}'/>
        </body>
    </html>"""

    
    return  HTMLResponse(content=html_content, status_code=200)    




# functionality(?)
def find_subbed_channels(channel_ID: str) -> dict:
    # use channel ID to find list of channels they are subscribed to
    ptoken = ""
    maxresults = 50
    # do a first request, take page info from it to determine if more requests needed
    req1 = youtube.subscriptions().list(
        part="id,snippet",
        channelId=channel_ID,
        maxResults=maxresults,
        pageToken=ptoken,
        fields="items(id,snippet(title)),nextPageToken,pageInfo"
    )
    resp1 = req1.execute()

    # compile results
    totalresults = resp1['pageInfo']['totalResults']
    listofchannels = []
    for item in resp1['items']:
        listofchannels.append(item['snippet']['title'])
    
    # do additional requests if necessary and continue adding results
    totalpages = m.ceil(totalresults / maxresults)
    if totalpages > 1:
        for _ in range(2):
            ptoken = resp1['nextPageToken']
            req1 = youtube.subscriptions().list(
                part="id,snippet",
                channelId=channel_ID,
                maxResults=maxresults,
                pageToken=ptoken,
                fields="items(id,snippet(title)),nextPageToken"
            )
            resp1 = req1.execute()
            for item in resp1['items']:
                listofchannels.append(item['snippet']['title'])

    output = {'totalSubs':totalresults, 'subbedChannels':listofchannels}
    return output

def find_channel_topics(channel_name: str) -> list:
    req = youtube.channels().list(
        part='topicDetails',
        forUsername=channel_name,
        fields='items(topicDetails(topicCategories))'
    )
    resp = req.execute()
    categorieslist = []
    if bool(resp):
        if bool(resp['items'][0]):
            categorieslist = resp['items'][0]['topicDetails']['topicCategories']
            categorieslist = [x.split('/')[-1] for x in categorieslist] # keep only category from link
    
    return categorieslist

