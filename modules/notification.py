from logbook import Logger, StreamHandler
import os
import requests
from dotenv import load_dotenv
load_dotenv()


class notification:

    def __init__(self):
        self.user = ''
        self.url = os.environ.get("message-url")

    def message(self, message, linkUrl=''):
        log = Logger(self.user)
        json = {"message" : message,
                "linkUrl" : linkUrl
        }
        try:
            requests.post(self.url, json=json, headers={ "Content-Type" : "application/json" })
        except Exception as e:
            print(f"notification could not be send: {e}")

        log.info(f'📨 send message:"{message}"')