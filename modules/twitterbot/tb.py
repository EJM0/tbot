from .db import *
from ..tiktok.upload import tiktok_upload
from ..twitter import *
from .percentofmood import moodpercent
from .countwords import countsaidwords
from .notification import notification
from .mulitthread_vosk import startanalysing
import re
from vosk import SetLogLevel
from moviepy.config import change_settings
from moviepy.editor import *
from time import sleep
import time
from datetime import timedelta, datetime
from ast import Try
from genericpath import exists
import json
import os
import logbook
import sys
from dotenv import load_dotenv
load_dotenv()
change_settings({"FFMPEG_BINARY": "ffmpeg"})


listname = os.environ.get("channel-config")
channelconfraw = open(listname, "r")
channelconf = json.load(channelconfraw)

options_codec = os.environ.get("codec")


class wordprep:
    sentence_list = []

    def __init__(self, workdir, vfile):
        # look if path has / at end of string. if not add it

        SetLogLevel(-1)

        if workdir[-1] == '/':
            self.workdir = workdir
        elif workdir[-1] != '/':
            self.workdir = workdir+'/'

        self.vfile = vfile
    # obsolete
    """ def convertevideotowav(self):
        self.log.info('converting')
        sound = AudioFileClip(os.path.join(self.workdir,self.vfile))
        sound.write_audiofile(self.afilename, fps=44100, nbytes=2, buffersize=2000, ffmpeg_params=["-ac", "1"], write_logfile=False, verbose=True)
    """

    def analyse(self):
        return startanalysing(os.path.join(self.workdir, self.vfile), self.workdir)


class trimming:
    noti = notification()

    def __init__(self, log, results, workdir, vfile, word, channel, startpadding=0.7, endpadding=0.5, addittion=None):
        self.log = log
        self.workdir = workdir
        self.vfile = vfile
        self.word = word
        self.channel = channel
        self.startpadding = startpadding
        self.endpadding = endpadding
        self.results = results
        self.editlist = []
        self.uploadlist = []
        self.jsonwordlist = []
        self.addition = addittion

    def timeconv(self, intime):
        return str(timedelta(seconds=intime))[:-4]

    def trim_on_word(self):
        self.log.info(self.word)
        self.log.info("snipping")
    # with open(os.path.join(self.workdir, 'output.txt'), 'r') as fr:
        for line in self.results:
            # line = str(line.rstrip())
            line = line.replace("\"", ",")
            line = line.replace("\'", "\"")
            self.jsonwordlist.append(line)

        count = 0
        for line in self.jsonwordlist:
            try:
                line = json.loads(line)
                if len(line) == 0 or len(line) == 1:
                    pass
                elif line['word'] in self.word and line['conf'] >= 0.85:
                    count = count + 1
            except:
                pass

        if count == 0:
            self.log.warning('passing because no words to process')
            return

        self.log.info(f'{count} {self.word}\'s in file')
        self.log.info('appending to cutting list ...')
        self.noti.message(f'there are {count} {self.word}, to be processed')

        if os.path.isdir(os.path.join(self.workdir, 'output')) == False:
            os.mkdir(os.path.join(self.workdir, 'output'))
        with VideoFileClip(os.path.join(self.workdir, self.vfile)) as vvar:
            for line in self.jsonwordlist:
                x = None
                try:
                    line = json.loads(line)
                    if len(line) == 0 or len(line) == 1:
                        pass
                    elif line['word'] in self.word and line['conf'] >= 0.8:
                        fstart = line['start']
                        fend = line['end']
                        start = fstart - self.startpadding
                        end = fend + self.endpadding
                        # print('word:', line['word'], 'start:', self.timeconv(start), 'end:', self.timeconv(end))
                        endtimecode = self.timeconv(end)
                        # vodfile = line['word']+'-' + endtimecode.replace(":", ".")+'.mp4'
                        # print(start, end)
                        x = vvar.subclip(start, end)
                except:
                    # print('couldn\'t load line')
                    pass
                if x is not None:
                    try:
                        if x == None:
                            pass
                        else:
                            self.editlist.append(x)
                        # print('append to list\n')
                    except Exception as e:
                        self.log.error('there was n error with  appending the file:'+str(e)+'\n'+line)

            self.log.info("stitching")

            if self.addition != None:
                filename = f'{self.addition}stitched-video.mp4'
            else:
                filename = 'stitched-video.mp4'

            odir = os.getcwd()
            os.chdir(os.path.join(self.workdir, 'output/'))

            final_clip = concatenate_videoclips(self.editlist)
            # final_clip.write_videofile(workdir+'output/'+'stitched-video-nonf.mp4')
            final_clip.write_videofile(os.path.join(self.workdir, 'output/', filename), fps=30, verbose=False, remove_temp=True,
                                       audio_codec="aac", codec=options_codec, bitrate='5M', preset='medium', threads=16, logger=None)

            os.chdir(odir)

            self.log.info('closing all clips')
            for x in self.editlist:
                x.close()
            vvar.close()
            final_clip.close()
        """ subprocess.call(['ffmpeg', '-loglevel', 'quiet', '-err_detect', 'ignore_err', '-i', os.path.join(self.workdir,'output/','stitched-video-nonf.mp4'), '-c', 'copy', os.path.join(self.workdir,'output/','stitched-video.mp4'), '-y'])
        os.remove(os.path.join(self.workdir,'output/','stitched-video-nonf.mp4')) """

    def twitter_upload(self):
        sleep(20)

        clip = VideoFileClip(os.path.join(
            self.workdir, 'output/', 'stitched-video.mp4'))
        duration = clip.duration
        clip.close()

        self.log.info(f'duration: {duration}')
        if duration > 120:
            timessecons = duration // 120
            rest = duration % 120
            startsec = 0
            endsec = 120
            n = 0
            while n != timessecons:
                start = 120 * n
                end = 120 * n + 120
                #print('n', start, end)

                odir = os.getcwd()
                os.chdir(os.path.join(self.workdir, 'output/'))

                clip = VideoFileClip(os.path.join(
                    self.workdir, 'output/', 'stitched-video.mp4')).subclip(start, end)
                clip.write_videofile(os.path.join(self.workdir, 'output/'+str(n)+'-part.mp4'), fps=30, verbose=False, remove_temp=True,
                                     audio_codec="aac", codec=options_codec, bitrate='5M', preset='medium', threads=16, logger=None)
                clip.close()

                os.chdir(odir)

                self.uploadlist.append(str(n)+'-part.mp4')
                n += 1
            if rest != 0:
                clip = VideoFileClip(os.path.join(
                    self.workdir, 'output/', 'stitched-video.mp4'))
                duration = clip.duration
                #print(timessecons, duration)
                start = 120 * timessecons
                end = start + rest
                #print('rest', start, end)

                odir = os.getcwd()
                os.chdir(os.path.join(self.workdir, 'output/'))

                clip = clip.subclip(start, end)
                clip.write_videofile(os.path.join(self.workdir, 'output/'+str(rest)+'-part.mp4'), fps=30, verbose=False,
                                     remove_temp=True, audio_codec="aac", codec=options_codec, bitrate='5M', preset='medium', threads=16, logger=None)
                clip.close()

                os.chdir(odir)

                self.uploadlist.append(str(rest)+'-part.mp4')

        sleep(10)
        
        if len(self.uploadlist) != 0:
            #self.log.info(len(self.uploadlist))
            self.log.info(f'{self.uploadlist} videos to upload')
            self.log.info('uploading ...')
            for c, ugoal in enumerate(self.uploadlist, start=1):
                self.log.info(f'upload-{c}: {ugoal}')
                tweet_media(self.workdir+'/output/'+ugoal, '#' +
                            self.channel+' '+str(c)+'/'+str(len(self.uploadlist)))
        else:
            self.log.info('uploading')
            tweet_media(self.workdir+'/output/' +
                        'stitched-video.mp4', '#'+self.channel)
        return


class sentimenttweet:

    def __init__(self, log, channel, aresults, workdir, dbid=''):
        self.log = log
        self.channel = channel
        self.aresults = aresults
        self.workdir = workdir
        self.dbid = dbid

    def tweetsentiment(self):

        if self.aresults == []:
            self.log.info('no results to process')
            if os.environ.get("db-host"):
                db = database()
                db.dump_array_via_id(self.dbid, 'emotions', [])
        else:
            if self.dbid != '':
                moodpercent(self.aresults, self.channel, dbid=self.dbid)
            else:
                moodpercent(self.aresults, self.channel)

            countsaidwords(self.aresults, self.workdir, self.channel)


class init:
    def __init__(self, path, word, sp=5, ep=3, channel='', test=False, dbid=None, addittion=None):
        logbook.StreamHandler(sys.stdout).push_application()
        self.log = logbook.Logger(channel)
        
        patharray = path.split('/')
        self.workdir = "/".join(patharray[:-1])
        self.log.info(f'working dir set to: {self.workdir}')
        self.vfile = patharray[-1:][0]
        self.log.info(f'filename: {self.vfile}')
        
        self.word = word
        self.channel = channel
        self.dbid = dbid
        self.addittion = addittion
        match = re.search(r'\d{4}-\d{2}-\d{2}', path)
        
        if match:
            self.date = match.group()
        else:
            self.log.warning('no match for date in path string!')
            self.date = None
        try:
            if channelconf['streamers'][channel]['tbot']['start'] and channelconf['streamers'][channel]['tbot']['end']:
                self.sp = channelconf['streamers'][channel]['tbot']['start']
                self.ep = channelconf['streamers'][channel]['tbot']['end']
        except:
            self.log.warning('start/end puffer not defined setting standart values')
            self.sp = sp
            self.ep = ep
        self.test = test
        self.log.info(f'|{self.sp}| + |video| + |{self.ep}|')

    def start(self):
        """cv = combinevids(self.workdir)
        """
        # start word recognition or load tempfile
        if self.test == 0 or 3 or 4 or 5:
            wp = wordprep(self.workdir, self.vfile)
            if os.path.isfile(os.path.join(self.workdir, 'output.txt')) == True:
                self.log.info('skipping analyse output.txt exists!')
                aresults = []
                with open(os.path.join(self.workdir, 'output.txt'), 'r') as fr:
                    for line in fr:
                        # line = str(line.rstrip())
                        aresults.append(line)
            else:
                start = time.time()
                aresults = wp.analyse()
                self.log.info(f'time elapsed: {datetime.fromtimestamp(time.time()-start).strftime("%H:%M:%S")}')

                sleep(10)
        # database upload words
        if self.test == False and self.dbid != None:
            self.log.info('uploading word to db')
            dbres = []
            for line in aresults:
                try:
                    try:
                        line = str(line.rstrip())
                    except:
                        pass
                    line = line.replace("\"", ",")
                    line = line.replace("\'", "\"")
                    line = json.loads(line)
                    if len(line) == 0 or len(line) == 1:
                        pass
                    else:
                        dbres.append([line['start'], line['end'],
                                     line['word'], line['conf']])
                except:
                    pass
            db = database()
            db.dump_array_via_id(self.dbid, 'words', dbres)
            db.cd()

        # trim word to right lengt
        if self.test == 0 or 1 or 4 or 5 or 6:
            self.log.info('trimming words')
            # trimming and concating video also uplad to twitter
            tr = trimming(self.log, aresults, self.workdir, self.vfile, self.word,
                          self.channel, self.sp, self.ep, self.addittion)
            tr.trim_on_word()

        # do histogramm and Vader analytics
        if self.test == 0:
            # tweet sentiment analyses
            self.log.info('Vader analytic and histogram')
            st = sentimenttweet(self.log, self.channel, aresults,
                                self.workdir, dbid=self.dbid)
            st.tweetsentiment()

        if self.test == 0 or 6:
            self.log.info('upload to twitter')
            tr.twitter_upload()
            self.log.info('upload to twitter finished')
            
        """ if channelconf['streamers'][self.channel]['tbot']['tiktokupload'] and self.date != None and channelconf['streamers'][self.channel]['tbot']['tiktokupload'] == True:
            tiktok_upload(self.channel, self.date, os.path.join(
                self.workdir, 'output/', 'stitched-video.mp4')) """
        
        if self.test == 0:
            try:
                # os.remove(os.path.join(self.workdir, 'output.txt'))
                # os.remove(os.path.join(self.workdir, self.vfile))
                pass
            except Exception as e:
                self.log.error('faild to delete temp files', e)
                
        return
