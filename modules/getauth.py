import json
import os
import time

import dotenv
import requests
from aiohttp import client
from logbook import Logger, StreamHandler
import datetime

from modules.notification import notification

noti = notification()
dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)
clientid = os.environ.get("Client-ID-Twitch")
clientsecret = os.environ.get("Authorization-Twitch")

def post(user = 'token'):
    log = Logger(user)
    daysec = 2456000
    url = 'https://id.twitch.tv/oauth2/token?client_id='+clientid+'&client_secret='+clientsecret+'&grant_type=client_credentials'
    req = requests.post(url)
    jsondata = req.json()
    token = jsondata['access_token']
    wait = jsondata['expires_in']-daysec

    log.info('🔑 getting token')
    #log.info(jsondata)
    log.info('🔑 auth token is = '+token)
    days = wait // (24 * 3600)
    log.info('💤 sleeps for '+str(wait)+'s or '+str(days)+'d')

    wait = wait + time.time()
    
    noti.message('new token generated in '+user+' for '+str(days)+'days! ' + token)

    return wait, token

