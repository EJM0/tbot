""" import asyncio
from websockets.server import serve
from multiprocessing import Process, SimpleQueue
import json
import subprocess

workdir = '/Volumes/twitchbot/twitch/' #smb share of the other server to get access of the videos

async def jetj(websocket, q):
    async for message in websocket:
        try:
            q.put(json.loads(message))
            await websocket.send('1')
        except:
            pass
        
#dunno chatqpt knows for shure :)
def start_server(q):
    async def main():
        async with serve(lambda websocket, path: jetj(websocket, q), "0.0.0.0", 8766):
            await asyncio.Future()  # run forever

    asyncio.run(main())

#compress tha shit
def compressfile(r):
    print('start compressing')
    subprocess.call(['ffmpeg', '-y', '-loglevel', 'quiet', '-i', workdir+r[1]+'/'+r[1]+'-stream-'+r[2]+'/'+r[3], '-c:v', 
'h264_videotoolbox', '-crf', '21', '-preset', 'faster', '-c:a', 'copy', workdir+r[1]+'/'+r[1]+'-stream-'+r[2]+'/'+r[4]])
    print('finished')

if __name__ == '__main__':
    #setup websock listener
    q = SimpleQueue()
    server_process = Process(target=start_server, args=(q,))
    server_process.start()

    #do smth with the response
    while True:
        r = q.get()
        print(r)
        if r[0] == 'compress':
            Process(target=compressfile, args=(r,)).start() """
            
import asyncio
import websockets
import subprocess
import multiprocessing

workdir = '/home/tbot/twitchbot/modules/tiktok/chrome-linux64/chrome' #smb share of the other server to get access of the videos

def start_subprocess(r):
    print(workdir+r[1]+'/'+r[1]+'-stream-'+r[2]+'/'+r[3])
    print(workdir+r[1]+'/'+r[1]+'-stream-'+r[2]+'/'+r[4])
    command = ['ffmpeg', '-y', '-loglevel', 'quiet', '-i', workdir+r[1]+'/'+r[1]+'-stream-'+r[2]+'/'+r[3], '-c:v', 
'h264_videotoolbox', '-crf', '21', '-preset', 'faster', '-c:a', 'copy', workdir+r[1]+'/'+r[1]+'-stream-'+r[2]+'/'+r[4]]
    subprocess.call(command)


async def websocket_handler(websocket):
    async for message in websocket:
        if message[0] == 'compress':
            print(message)
            """ process = multiprocessing.Process(target=start_subprocess, args=(message,))
            process.start() """

async def main():
    async with websockets.serve(lambda websocket, path: websocket_handler(websocket), "0.0.0.0", 8767):
            await asyncio.Future()

asyncio.run(main())
