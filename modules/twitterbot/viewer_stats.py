import chunk
import modules.checkstream as checkstream
from ..twitter import *
import datetime
from datetime import timedelta
import requests
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
import uuid
import socket
import time
import json
import plotly.figure_factory as ff
import pandas as pd
from multiprocessing import Process, Queue
from modules.twitterbot.GerVADER.vaderSentimentGER import SentimentIntensityAnalyzer
from modules.twitterbot.db import *
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import numpy as np
from collections import defaultdict
import logbook
import sys
load_dotenv()


class vstats():

    def __init__(self, token, stime, workdir, channel, dbid, exittime=900, test=None):
        logbook.StreamHandler(sys.stdout).push_application()
        self.log = logbook.Logger(channel)

        self.client_id = os.environ.get("Client-ID-Twitch")
        self.token = token
        self.stime = stime
        self.channel = channel
        self.dbid = dbid
        self.vad = SentimentIntensityAnalyzer()
        self.fileq = Queue()
        self.arrayq = Queue()
        self.test = test
        self.exittime = exittime

        self.workdir = os.path.join(workdir, 'analytics/')
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)

        # chat record vars
        self.bigbuarray = []

        # viewer stats vars
        self.x_values = []
        self.y_values = []
        self.change_title = []
        self.categorylegend = []
        self.gns = []
        self.dbarray = []
        self.legendcount = 0

        # Check for temp files
        self.log.info('checking for files')
        if os.path.exists(os.path.join(workdir, 'analytics/chat.tmp')):
            self.log.info('found previous temp file, loading it ...')
            # Load tmp file
            with open(os.path.join(workdir, 'analytics/chat.tmp'), 'r') as temp_file:
                content = temp_file.read()
                for line in content.split('\n'):
                    try:
                        line = line.strip()
                        data = json.loads(line)
                        if not line:
                            continue
                        else:
                            self.bigbuarray.append(data)
                    except:
                        pass
        self.ctmpfile = open(os.path.join(self.workdir, 'chat.tmp'), 'a+')

        if os.path.exists(os.path.join(self.workdir, 'vstats.tmp')):
            self.log.info('found previous temp file, loading it ...')
            # Load tmp file
            with open(os.path.join(workdir, 'analytics/vstats.tmp'), 'r') as temp_file:
                content = temp_file.read()
                for line in content.split('\n'):
                    line = line.strip()  # Strip leading and trailing whitespaces
                    if not line:
                        continue  # Skip empty lines
                    data = json.loads(line)
                    if data != None:
                        time = float(data['time'])
                        if data['gamename'] != None:
                            self.categorylegend.append(data['categorylegend'])
                            self.gns.append(data['gamename'])
                            self.legendcount = data['lc']
                        if data['changedtitle'] is not None:
                            self.change_title.append([datetime.datetime.fromisoformat(
                                data['changedtitle'][0]), data['changedtitle'][1]])
                        if data['x'] != None and data['y'] != None:
                            self.x_values.append(
                                datetime.datetime.fromisoformat(data['x']))
                            self.y_values.append(data['y'])
            # os.remove(os.path.join(workdir, 'analytics/vstats.tmp'))
        self.tmpfile = open(os.path.join(
            workdir, 'analytics/vstats.tmp'), 'a+')
        sys.stdout.flush()

        # start process
        if test == None:
            pass
            self.start()

    def collect_data(self):
        url = f'https://api.twitch.tv/helix/streams?user_login={self.channel}'
        API_HEADERS = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.token}',
        }

        # Function to load and resize image
        def load_and_resize_image(game_id):
            url = f'https://api.twitch.tv/helix/games?id={game_id}'
            response = requests.get(url, headers=API_HEADERS)
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                game_info = data['data'][0]
                category_picture_url = game_info['box_art_url'].replace(
                    '{width}x{height}', '1520x2048')
            else:
                return None

            response = requests.get(category_picture_url)

            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                return img
            else:
                self.log.error(
                    f"Error fetching image for category '{game_id}'. Status code: {response.status_code}")
                return None

        # Function to retrieve data from Twitch API

        def get_data(type=None):
            req = requests.get(url, headers=API_HEADERS)
            jsondata = req.json()
            try:
                if type == None:
                    return jsondata['data'][0]
                else:
                    return jsondata['data'][0][type]
            except:
                return None

        name = str(uuid.uuid4())+'.png'
        filename = os.path.join(self.workdir, name)
        dbarray = []
        old_title = get_data('game_id')
        nt = get_data('game_name')
        if self.test != None:
            exittime = time.time() + self.test

        chuck = {'time': str(time.time()), 'categorylegend': None,
                 'changedtitle': None, 'gamename': None, 'x': None, 'y': None, 'lc': None}

        date = datetime.datetime.now()
        self.x_values.append(date)
        chuck['x'] = date.isoformat()
        viewer = get_data('viewer_count')
        self.y_values.append(viewer)
        chuck['y'] = viewer

        # need to check if last game was in temp if temp was loaded
        reversed_gns = self.gns[::-1]
        if reversed_gns == [] or reversed_gns[0] != get_data('game_name'):
            if reversed_gns == []:
                self.change_title.append([date, get_data('game_id')])
                chuck['changedtitle'] = [date.isoformat(), get_data('game_id')]
                self.gns.append(get_data('game_name'))
                chuck['gamename'] = get_data('game_name')
                self.categorylegend.append(f'start: {nt}\r')
                chuck['categorylegend'] = f'start: {nt}\r'
            else:
                self.change_title.append([date, get_data('game_id')])
                chuck['changedtitle'] = [date.isoformat(), get_data('game_id')]
                self.gns.append(get_data('game_name'))
                chuck['gamename'] = get_data('game_name')
                gn = get_data('game_name')
                self.categorylegend.append(f'{str(self.legendcount)}: {gn}\r')
                chuck['categorylegend'] = f'{str(self.legendcount)}: {gn}\r'
            chuck['lc'] = self.legendcount

        chuck_json_string = json.dumps(chuck)
        self.tmpfile.write(str(chuck_json_string)+'\n')
        self.tmpfile.flush()

        self.log.info('starting loop')
        while True:
            # data structure dict
            chuck = {'time': str(time.time()), 'categorylegend': None,
                     'changedtitle': None, 'gamename': None, 'x': None, 'y': None, 'lc': None}

            if self.test != None and exittime <= time.time():
                break

            try:
                chname = None
                time.sleep(self.stime)

                try:
                    viewer = get_data('viewer_count')
                    now_title = get_data('game_id')
                    # Added to retrieve the game name
                    gn = get_data('game_name')

                    if now_title != old_title and now_title != None:
                        self.legendcount += 1
                        old_title = now_title
                        chuck['categorylegend'] = f'{str(self.legendcount)}: {gn}\r'
                        # Include game name in the legend
                        self.categorylegend.append(
                            f'{str(self.legendcount)}: {gn}\r')
                        chname = now_title
                        chuck['changedtitle'] = [
                            datetime.datetime.now().isoformat(), now_title]
                        self.change_title.append(
                            [datetime.datetime.now(), now_title])
                        chuck['gamename'] = gn
                        self.gns.append(gn)
                        chuck['lc'] = self.legendcount
                except:
                    break

                if checkstream.checkUser(self.channel, self.token) == True:
                    data = datetime.datetime.now()
                    self.x_values.append(data)
                    chuck['x'] = data.isoformat()
                    self.y_values.append(viewer)
                    chuck['y'] = viewer

                    if chname != None:
                        dbarray.append([time.time(), data, viewer, chname])
                    else:
                        dbarray.append([time.time(), data, viewer])
                elif checkstream.checkUser(self.channel, self.token) == False:
                    self.log.info('pre exit plotting waiting 15min')
                    sys.stdout.flush()
                    time.sleep(self.exittime)

                    if checkstream.checkUser(self.channel, self.token) == False:
                        self.log.info('exiting plotting')
                        self.tmpfile.close()
                        break
                    else:
                        pass
                chuck_json_string = json.dumps(chuck)
                self.tmpfile.write(str(chuck_json_string)+'\n')
                self.tmpfile.flush()
            except KeyboardInterrupt:
                self.log.info("Keyboard interrupt detected. Exiting loop...")
                exit()
        if os.environ.get("db-host"):
            db = database()
            db.dump_array_via_id(self.dbid, 'viewotime', dbarray)
            db.cd()

        # Generate random vertical lines
        image_paths = [x[1] for x in self.change_title]
        # Generate random data for the graph

        # Plot the graph and add indicators
        plt.style.use('dark_background')
        fig, ax = plt.subplots()
        ax.plot(self.x_values, self.y_values, label='viewers')

        xs = [x[0] for x in self.change_title]
        xs = np.asarray(xs)
        ax.vlines(xs, 0, ax.get_ylim()[1], color='purple', lw=2, alpha=0.7)

        scaled_images_info = [load_and_resize_image(
            path) for path in image_paths]

        scalingfactor = 0.03
        for (x, img, gn) in zip(xs, scaled_images_info, self.gns):
            try:
                if img:
                    img_width, img_height = img.size
                    scaled_width = int(img_width * scalingfactor)
                    scaled_height = int(img_height * scalingfactor)
                    imge = img.resize((scaled_width, scaled_height))
                    ab = AnnotationBbox(OffsetImage(
                        imge), (x, 1), frameon=False)
                    ax.add_artist(ab)

                    # Add text below the image containing the game name
                    # bbox_props = dict(boxstyle="square", facecolor="white", edgecolor="black", linewidth=2)  # Specify bounding box properties
                    ax.text(x, -scaled_height*2.4,
                            f'{gn}', ha='center', va='top', color='white', fontsize=5,)
            except Exception as e:
                self.log.info(f"Error adding AnnotationBbox: {e}")
                sys.stdout.flush()

        ax.legend()

        # Show the plot
        plt.savefig(filename, dpi=300)
        plt.close()
        self.fileq.put([filename, self.categorylegend])
        return filename
        # os.remove(filename)

    def connect_to_twitch_chat(self):
        server = 'irc.chat.twitch.tv'
        port = 6667
        irc = socket.socket()
        irc.settimeout(3)
        irc.connect((server, port))
        irc.send(f'NICK justinfan12345\n'.encode('utf-8'))
        irc.send(f'JOIN #{self.channel}\n'.encode('utf-8'))
        return irc

    def read_chat(self):
        buffer = ''
        try:
            buffer += self.irc.recv(2048).decode('utf-8')
            if buffer == "PING :tmi.twitch.tv\r\n":
                self.irc.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            lines = buffer.split('\n')
            buffer = lines.pop()
            for line in lines:
                if "PRIVMSG" in line:
                    username = line.split('!')[0][1:]
                    message = ':'.join(line.split(':')[2:])
                    return username, message, time.time()
        except Exception as e:
            return None

    def collect_chat(self):
        c = time.time() + 240
        timeout = 0
        self.irc = self.connect_to_twitch_chat()

        try:
            while True:
                try:
                    c += 1
                    message = self.read_chat()
                    if message != None:
                        timeout = 0
                        self.bigbuarray.append(message)
                        self.ctmpfile.write(json.dumps(message)+'\n')
                        self.ctmpfile.flush()
                    elif message == None:
                        timeout += 1
                    if timeout == 100:
                        time.sleep(5)
                        try:
                            self.irc.close()  # Close the socket connection
                            self.irc = None
                            self.irc = self.connect_to_twitch_chat()
                        except:
                            pass
                    if c <= time.time() or timeout >= 20:
                        c = time.time() + 240
                        if checkstream.checkUser(self.channel, self.token) == False:
                            self.log.info('pre exit chat waiting 15min')
                            sys.stdout.flush()
                            time.sleep(self.exittime)
                            if checkstream.checkUser(self.channel, self.token) == False:
                                self.log.info('exiting chat')
                                try:
                                    self.irc.close()  # Close the socket connection
                                except:
                                    pass
                                self.ctmpfile.close()
                                break
                except Exception as e:
                    self.log.error(f'main error: {e}')
        except KeyboardInterrupt:
            self.log.info("Keyboard interrupt detected. Exiting loop...")
            exit()

        if os.environ.get("db-host"):
            # write to db
            db = database()
            db.dump_array_via_id(self.dbid, 'topchatter', self.bigbuarray)
            db.cd()

        self.log.info('plotting messages')
        # Convert to a DataFrame and remove the Timestamp
        timestamps = [sublist[:3] for sublist in self.bigbuarray]
        df = pd.DataFrame(self.bigbuarray, columns=[
                          'username', 'message', 'timestamp'])
        df = df[['username', 'message']]  # Keep only 'username' and 'message'

        # Count the number of messages per user
        message_counts = df['username'].value_counts().reset_index()
        message_counts.columns = ['username', 'messages']

        # Keep only the top 10
        top = message_counts.head(10)
        fig = ff.create_table(top)
        fig.update_layout(
            template="plotly_dark",  # Use Plotly's dark theme
            autosize=False,
            width=500,
            height=200,
        )

        name = str(uuid.uuid4())+'.png'
        filename = os.path.join(self.workdir, name)
        self.log.info('ploting table')
        fig.write_image(filename, scale=2)

        message_dis_name_path = os.path.join(
            self.workdir, str(uuid.uuid4())+'.png')

        # Convert timestamps to datetime object
        timestamps = [float(timestamp) for _, _, timestamp in timestamps]

        # Define bin size (in minutes)
        bin_size = timedelta(minutes=10)  # 10 minutes

        # Calculate message distribution over time using binning
        distribution = defaultdict(int)
        for timestamp in timestamps:
            dt = datetime.datetime.fromtimestamp(timestamp)
            bin_start = dt - (dt - datetime.datetime.min) % bin_size
            distribution[bin_start] += 1


        # Extract sorted dates and counts
        sorted_distribution = sorted(distribution.items())
        dates, counts = zip(*sorted_distribution)

        # Calculate density of messages for each time interval
        message_density = np.array([distribution[dt]
                                   for dt, _ in sorted_distribution])

        # Create the plot
        plt.figure(figsize=(12, 6))
        plt.style.use('dark_background')
        bar_width = 0.8  # Adjust the width of each bar
        plt.bar(range(len(message_density)), message_density, color=plt.cm.hot(
            message_density / max(message_density)), width=bar_width)
        plt.title('Message Density Over Time')
        plt.xlabel('Time Interval')
        plt.ylabel('Message Count')

        # Show only every 10th x-axis label
        x_labels = [dt.strftime('%H:%M') for dt, _ in sorted_distribution]
        plt.xticks(np.arange(0, len(dates), 10), x_labels[::10], rotation=90)

        plt.tight_layout()
        plt.savefig(message_dis_name_path, dpi=300)
        plt.close()

        self.arrayq.put([filename, message_dis_name_path])

    def start(self):
        cd = Process(target=self.collect_data)
        vs = Process(target=self.collect_chat)

        # Start and join the 'collect_data' process first
        cd.start()
        # After 'collect_data' completes, start the 'collect_chat' process
        vs.start()

        vs.join()
        cd.join()

        # Now retrieve the results
        f = self.fileq.get()
        a = self.arrayq.get()

        self.log.info('done')
        try:
            os.remove(os.path.join(self.workdir, 'vstats.tmp'))
            os.remove(os.path.join(self.workdir, 'chat.tmp'))
        except Exception as e:
            self.log.warning(f'not able to delete tempfiles: {e}')

        tweet_pics(
            [f[0], a[0], a[1]], f"chart of viewercount and top messages of stream from: {self.channel}\r\r{''.join(f[1])}")