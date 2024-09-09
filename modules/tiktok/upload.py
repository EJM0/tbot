import os
from dotenv import load_dotenv
load_dotenv()
from tiktok_uploader.upload import upload_video, upload_videos
from tiktok_uploader.auth import AuthBackend
from selenium.webdriver.chrome.options import Options

cookies = os.environ.get("session-cookies")
print(cookies)

def tiktok_upload(channel, date, videopath):
    

    options = Options()

    # define path of selenium webdriver  and headless mode disable gpu acceleration  # Disables the sandbox
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    # Overcomes limited resource problems  # Applicable to headless mode  # Runs Chrome in headless mode (without GUI)

    upload_video(videopath,
            description=f'Zusammenfassung von {channel} am {date} #foryou #foryoupage #fyp #streaming #twitch #hightlight #{channel} #{channel}twitch #funny #germantwitch #lol',
            cookies=cookies,
            headless=True,
            options=options)

    videos = [
        {
            'video': videopath,
            'description': f'Zusammenfassung von {channel} am {date} #foryou #foryoupage #fyp #streaming #twitch #hightlight #{channel} #{channel}twitch #funny #germantwitch #lol'
        }
    ]

    auth = AuthBackend(cookies=cookies)
    upload_videos(videos=videos, auth=auth, headless=True, options=options)

