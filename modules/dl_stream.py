from modules.twitterbot import tb
import os
import subprocess
import time
from datetime import date, datetime
from multiprocessing import Process, Semaphore

import re
import glob
from logbook import Logger
from moviepy.editor import *
import json
import shutil

from modules.twitterbot.fckdmca import dmcaf
import modules.twitterbot.youtube_upload as ytupload
from modules.notification import notification
import modules.checkstream as checkstream
""" from modules.compress_server_client import job """

noti = notification()

listname = os.environ.get("channel-config")
channelconfraw = open(listname, "r")
channelconf = json.load(channelconfraw)

options_codec = os.environ.get("codec")
cs = True if channelconf.get('compress-server') else False
num = 0
pool_sema = Semaphore(6)
clip_start = 0


def get_file_size_in_gb(file_path):
    size_in_bytes = os.path.getsize(file_path)
    size_in_gb = size_in_bytes / (1024 * 1024 * 1024)
    return "{:.2f} GB".format(size_in_gb)


def extract_time(filename):
    # Extrahiere die Uhrzeit (HH.MM) aus dem Dateinamen
    time_str = os.path.splitext(filename)[0]
    try:
        hours, minutes = map(int, time_str.split('.'))
        return hours, minutes
    except ValueError:
        # Wenn der Dateiname nicht dem erwarteten Muster entspricht, wird die Datei am Ende sortiert
        return 24, 0


def dek(workdir, tempfilename, channel, log, token, pausetime=720):
    noti.message(f"starting download of: {channel}")
    log.info("⬇️ download started")

    try:
        print(channel)
        process = subprocess.Popen(["streamlink", "twitch.tv/" + channel, 'best', "-o", workdir+tempfilename,
                        '-l', 'none', '--hls-duration', '24:00:00', '--twitch-disable-ads'], stdout=subprocess.DEVNULL)
        try:
            process.wait()
        except KeyboardInterrupt:
            log.info("🔴 Graceful shutdown initiated")
            process.terminate()
            process.wait()
            log.info("🔴 Streamlink process terminated gracefully")
        except SystemExit:
            log.info("🔴 SystemExit received, forcefully killing the process")
            process.terminate()
            process.wait()
            log.info("🔴 Streamlink process killed forcefully due to SystemExit")
    except Exception as e:
        log.info(e)

    waittime = time.time()
    log.info('⚠️ lost stream')
    while True:
        if time.time() - waittime >= pausetime:
            break
        time.sleep(20)
        if checkstream.checkUser(channel, token) == True:
            log.info('❕ stream still active reopening download')
            return 'reopen'


def dlstream(channel, filename, workdir, token, ndate, dbid=None, udate=date.today()):
    log = Logger(channel)
    # os.chdir(folder)
    url = 'https://www.twitch.tv/' + channel

    # set file
    now = datetime.now()
    #filename = now.strftime("%H.%M")
    tempfilename = "temp_1_" + filename + ".mp4"

    streamcount = 0
    streamfiles = []

    while True:
        check = dek(workdir, filename+'_'+str(streamcount) +
                    '_stream.mp4', channel, log, token)
        streamfiles.append(workdir+filename+'_'+str(streamcount)+'_stream.mp4')
        streamcount += 1
        if check != 'reopen':
            break

    if len(streamfiles) == 1:
        print(len(streamfiles))
        streamfilenames = streamfiles[0].split('/')[-1]
        print(f'renaming: {streamfilenames} ==> {tempfilename}')
        os.rename(streamfiles[0], workdir+tempfilename)
    log.info("🔴 Recording stream is done")
    
    mvp = Process(target=managing_video, args=(channel, filename, workdir, log, ndate, streamfiles, dbid, udate,))
    mvp.start()
    
def managing_video(channel, filename, workdir, log, ndate, streamfiles, dbid=None, udate=date.today()):
    tempfilename = "temp_1_" + filename + ".mp4"
    tempfilename5 = 'temp_1.5_' + filename + '.mp4'
    tempfilename2 = "temp_2_" + filename + ".mp4"
      
    if len(streamfiles) > 1:
        log.info('🪡 stitching streamfiles together')
        videos = []
        for stream in streamfiles:
            # Repair the mp4 file before appending to the video list
            repaired_stream = workdir + "repaired_" + os.path.basename(stream)
            subprocess.call(['ffmpeg', '-loglevel', 'quiet', '-err_detect', 'ignore_err',
                    '-i', stream, '-c', 'copy', repaired_stream])
            videos.append(VideoFileClip(repaired_stream))
            # Force remove the original stream file
            os.remove(stream)

        odir = os.getcwd()
        os.chdir(workdir)

        final = concatenate_videoclips(videos)
        final.write_videofile(workdir+tempfilename, fps=30, verbose=False, remove_temp=True,
                              audio_codec="aac", codec=options_codec, bitrate='5M', preset='medium', threads=16, logger=None)

        os.chdir(odir)

        # Clean up repaired files
        for repaired_stream in videos:
            os.remove(repaired_stream.filename)

        for vin in videos:
            vin.close()
        for streamfile in streamfiles:
            time.sleep(2)
            os.remove(streamfile)

    print(workdir+'*.mp4')
    prefiles = glob.glob(workdir+'/*.mp4')
    # prefiles.pop(workdir+filename)
    pattern = re.compile(r"\d\d\.\d\d_\d_stream\.mp4", re.IGNORECASE)
    for i in prefiles:
        i = i.split('/')
        if pattern.match(i[-1]):
            print(f'renaming: {i[-1]} ==> {i[-1][:5]+".mp4"}')
            os.rename(workdir+i[-1], workdir+i[-1][:5]+'.mp4')

    prestreamfiles = []
    print(workdir+'*.mp4')
    prefiles = glob.glob(workdir+'/*.mp4')
    # prefiles.pop(workdir+filename)
    opattern = re.compile(r"\d\d\.\d\d\.mp4", re.IGNORECASE)
    for i in prefiles:
        i = i.split('/')
        if opattern.match(i[-1]):
            prestreamfiles.append(i[-1])
    print(prestreamfiles)
    if prestreamfiles == []:
        pass
    else:
        sorted_mp4_files = sorted(prestreamfiles, key=extract_time)
        print(sorted_mp4_files)
        videos = []
        os.rename(workdir+tempfilename, workdir+'2'+tempfilename)
        for stream in sorted_mp4_files:
            videos.append(VideoFileClip(workdir+stream))
        videos.append(VideoFileClip(workdir+'2'+tempfilename))

        odir = os.getcwd()
        os.chdir(workdir)

        final = concatenate_videoclips(videos)
        final.write_videofile(workdir+tempfilename, fps=30, temp_audiofile=os.path.join(workdir, 'temp-audio.m4a'), verbose=False,
                              logger=None, remove_temp=True, codec=options_codec, audio_codec="aac", bitrate='5M', preset='medium')

        os.chdir(odir)

        for vin in videos:
            vin.close()
        os.remove(workdir+'2'+tempfilename)
        for stream in sorted_mp4_files:
            time.sleep(2)
            os.remove(workdir+stream)

    noti.message("download done, start fixing of: "+channel)

    log.info("🧰 managing")
    try:
        if 'tbot' in channelconf['streamers'][channel]:
            noti.message("start fixing")
            subprocess.call(['ffmpeg', '-loglevel', 'quiet', '-err_detect', 'ignore_err',
                            '-i', workdir+tempfilename, '-c', 'copy', workdir+tempfilename5])
            os.remove(workdir+tempfilename)
            log.info("🧰 file fixed")

            # wait for os to unlock file for futher use
            time.sleep(20)

            log.info("🐦 starting twitter_bot")
            noti.message("start twitterbot")
            try:
                tbs = tb.init(os.path.join(workdir, tempfilename5), channelconf['streamers'][str(
                    channel)]['tbot']['words'], channel=channel, dbid=dbid)
                tbs.start()
            except Exception as e:
                log.error(f"⚠️⚠️⚠️ Tbot process had an ERROR: {e}")
            if 'ytupload' in channelconf['streamers'][channel] and channelconf['streamers'][channel]['ytupload'] == True:
                p = Process(target=fixm, args=(workdir, tempfilename5,
                            tempfilename2, filename, log, 1, channel, ndate, udate,))
                p.start()
            else:
                p = Process(target=fixm, args=(workdir, tempfilename5,
                            tempfilename2, filename, log, 0, channel, ndate, udate,))
                p.start()
        elif 'ytupload' in channelconf['streamers'][channel] and channelconf['streamers'][channel]['ytupload'] == True:
                p = Process(target=fixm, args=(workdir, tempfilename,
                            tempfilename2, filename, log, 1, channel, ndate, udate,))
                p.start()
        else:
            p = Process(target=fixm, args=(workdir, tempfilename,
                        tempfilename2, filename, log, 0, channel, ndate, udate,))
            p.start()
    except Exception as e:
        log.info(e)

    return filename


def fixm(workdir, tempfilename, tempfilename2, filename, log, choosen, channel, ndate, udate=date.today()):
    time.sleep(25)
    log.info("⚙️ starting video managing routien")

    lt1 = tempfilename
    lt2 = tempfilename2
    fn = filename
    compress_command = ['ffmpeg', '-loglevel', 'quiet', "-vf", "format=yuv420p", '-i', os.path.join(workdir, lt1), '-c:v',
                            options_codec, '-preset', 'medium', '-c:a', 'copy', os.path.join(workdir, fn + ".mp4")]
    print(compress_command)
    
    if choosen == 0:
        if 'NOKEEP' in channelconf['streamers'][channel] and channelconf['streamers'][channel]['NOKEEP'] == True:
            log.info('NOKEEP on deleting all files!')
            shutil.rmtree(workdir, ignore_errors=True)
        else:
            """ if cs == True:
                job(channel, ndate, lt1, fn)
             else:
            """
            subprocess.call(compress_command)
            log.info("🧰 file compressed")

    elif choosen == 1:
        if 'fckdmca' in channelconf['streamers'][channel] and channelconf['streamers'][channel]['fckdmca']:
                killmusic = dmcaf(workdir, lt1)
                log.info('🎛️ sepperating vocal stem')
                killmusic.sepperate()
                log.info('🎛️ remuxing new audio with video')
                finalvideo = killmusic.patch()
                log.info('🎛️ done!')
                fworkdir = workdir + 'output/'
                
        else:
            fworkdir = workdir
            finalvideo = lt1
        vfile = VideoFileClip(os.path.join(
                    fworkdir, finalvideo))
        duration = vfile.duration
        vfile.close()
        if duration >= 43200:
            vlist = ytupload.yt_pre_splitter(fworkdir, finalvideo)
            log.info("⬆️ uploading to youtube")
            print(vlist)
            try:
                for n, vid in enumerate(vlist, start=1):
                    vid = ['/'.join(vid.split('/')[:-1]) +
                           '/', vid.split('/')[-1]]
                    print(vid)
                    ytupload.upload(vid[0], vid[1], str(
                        udate)+'/'+str(n), channel)
                    ydir = os.path.join(fworkdir, "ytsplits")
                    shutil.rmtree(ydir)
                """ for vid in vlist:
                    os.remove(vid) """
            except Exception as e:
                print(e)
                log.info("⬆️ youtube upload failed")

        else:
            ytupload.upload(fworkdir, finalvideo, udate, channel)
        if 'NOKEEP' in channelconf['streamers'][channel] and channelconf['streamers'][channel]['NOKEEP'] == True:
            log.info('NOKEEP on deleting all files!')
            shutil.rmtree(workdir)
        else:
            """ if cs == True:
                job(channel, ndate, lt1, fn)
            else: """
            old_gb = get_file_size_in_gb(workdir + lt1)
            start = time.time()
            subprocess.call(compress_command)
            log.info(
                f"🧰 file compressed in: {datetime.fromtimestamp(time.time()-start).strftime('%H:%M:%S')}, {old_gb} -> {get_file_size_in_gb(workdir+fn+'.mp4')}")

            if cs == True:
                pass
            else:
                try:
                    os.remove(workdir+lt1)
                    log.info("🗑️ deleted temp files!")
                except Exception as e:
                    log.error(f'faild to delete temp files: \n{e}')
