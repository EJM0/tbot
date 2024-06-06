import glob
from .video_splitter import call_outside
from ..twitter import *
from moviepy.editor import *
from simple_youtube_api.LocalVideo import LocalVideo
from simple_youtube_api.Channel import Channel
import os
import sys
from datetime import date
from dotenv import load_dotenv
load_dotenv()


dir = os.environ.get("dir")
dir += '/.yt-credentials'


def yt_pre_splitter(workdir, tempfilename):

    dir = os.path.join(workdir, "ytsplits")
    print(dir)
    try:
        os.mkdir(dir)
    except Exception as e:
        print(e, ", skipping step")
    call_outside(tempfilename, 40000, workdir, 'ytsplits')

    return glob.glob(os.path.join(workdir, "ytsplits/*.mp4"))


def indexcheck(list, index):
    try:
        list[index]
        return True
    except:
        return False


def upload(workdir, vid, vid_title, creator):
    channel = Channel()
    channel.login(os.path.join(dir, "client_secret.json"),
                  os.path.join(dir, "credentials.storage"))
    # setting up the video that is going to be uploaded
    print(f'Titel: {creator}: {vid_title}')
    video = LocalVideo(file_path=os.path.join(workdir, vid))

    # setting snippet
    print(f'{creator}: {vid_title}')
    video.set_title(f'{creator}: {vid_title}')
    video.set_description(f"stream backup of {creator}")
    video.set_tags(["stream", creator])
    video.set_category("entertainment")
    video.set_default_language("de-DE")

    # setting status
    video.set_privacy_status("unlisted")

    # uploading video and printing the results
    video = channel.upload_video(video)

    # tweeting video link
    tweet_text(
        f'📺 {str(creator)} YT-backup {str(vid_title)} \nhttps://www.youtube.com/watch?v={str(video.id)}')


if __name__ == "__main__":
    if indexcheck(sys.argv, 1) == True:
        print('starting upload')
        upload(sys.argv[1], sys.argv[2], date.today())
