from aiohttp import client
import requests
from dotenv import load_dotenv
import os
from logbook import Logger, StreamHandler

client_id=os.environ.get("Client-ID-Twitch")

def checkUser(userName, token): #returns true if online, false if not
    log = Logger(userName)
    url = 'https://api.twitch.tv/helix/streams?user_login='+userName
    #url = url.rstrip()
    client_id=os.environ.get("Client-ID-Twitch")

    load_dotenv()

    API_HEADERS = {
        'Client-ID' : client_id,
        'Authorization' : 'Bearer ' + token,
    }

    try:
        #logging.printlog("🔎 checking user: "+userName)

        req = requests.get(url, headers=API_HEADERS)
        jsondata = req.json()

        if len(jsondata['data']) == 1:
            return True

        else:
            return False
            
    except Exception as e:
        log.error("⁉️ Error checking user: ", e)
        return False

def get_title(userName, token):
    log = Logger(userName)
    url = 'https://api.twitch.tv/helix/streams?user_login='+userName
    #url = url.rstrip()
    client_id=os.environ.get("Client-ID-Twitch")

    load_dotenv()

    API_HEADERS = {
        'Client-ID' : '7613tns3t4kzf7r9d2b8y21znfwtv0',
        'Authorization' : 'Bearer ' + token,
    }

    try:
        #logging.printlog("🔎 checking user: "+userName)

        req = requests.get(url, headers=API_HEADERS)
        jsondata = req.json()
        if len(jsondata['data']) == 1:
            data = jsondata['data'][0]['title']
            #print(data)
            return jsondata['data'][0]['title']
            
    except Exception as e:
        log.error("⁉️ Error checking user: ", e)