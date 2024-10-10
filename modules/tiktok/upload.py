import requests
import json
from urllib.parse import urlencode, urlparse, parse_qs
import time
import random
import string
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import math
import sys
from multiprocessing import Process, Queue


path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(path)
from notification import notification  # Assuming this is your custom notification module

class TiktokUploader:
    def __init__(self, client_key, client_secret, redirect_uri, token_file=os.path.join(os.path.dirname(__file__), 'token.json')):
        self.csrf_state = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        self.client_key = client_key
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_file = token_file
        self.auth_code = None
        self.noti = notification()
        self.token_event = threading.Event()
        self.access_token = None

    def upload_to_tiktok(self, video_path):
        try:
            def check_token_file_process(self, queue):
                self.check_token_file()
                queue.put(self.access_token)

            def start_http_server_process(self, queue):
                self.start_http_server()
                queue.put(self.access_token)

            token_queue = Queue()
            file_process = Process(target=check_token_file_process, args=(self, token_queue,))
            server_process = Process(target=start_http_server_process, args=(self, token_queue,))

            file_process.start()
            server_process.start()
            
            # Wait for either process to finish and get the token
            access_token = token_queue.get()
            self.access_token = access_token

            # Forcefully terminate both processes
            file_process.kill()
            server_process.kill()

            # Wait for processes to finish
            file_process.join()
            server_process.join()

            video_size = os.path.getsize(video_path)
            upload_url, publish_id = self.get_upload_url(access_token, video_size)

            # Get chunk details based on the video size
            total_chunks, chunk_size, last_chunk_size = self.calculate_chunk_count(video_size)

            # Upload video in chunks
            self.upload_video(upload_url, video_path, video_size, total_chunks, chunk_size, last_chunk_size)

            # Poll for upload status
            status_response = self.get_post_status(access_token, publish_id)
            print("Video upload status:", status_response['data']['status'])

        except Exception as e:
            print("An error occurred:", str(e))

    def get_auth_code(self):
        auth_url = 'https://www.tiktok.com/v2/auth/authorize/'
        params = {
            'client_key': self.client_key,
            'response_type': 'code',
            'scope': 'video.upload,video.publish',
            'redirect_uri': self.redirect_uri,
            'state': self.csrf_state
        }
        auth_url = f"{auth_url}?{urlencode(params)}"
        print("Open the following URL in your browser to authorize:", auth_url)
        self.noti.message('!!!tiktok needs reauthentication!!!', auth_url)

    def start_http_server(self):
        uploader_instance = self

        class RequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                auth_code = query_params.get('code', [None])[0]
                if auth_code:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'Authorization successful. You can close this window.')
                    self.server.auth_code = auth_code
                    uploader_instance.auth_code = auth_code
                    uploader_instance.access_token = uploader_instance.request_new_access_token(auth_code)
                    uploader_instance.token_event.set()
                    threading.Thread(target=self.server.shutdown).start()
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'Authorization code not found.')

        self.get_auth_code()
        server = HTTPServer(('0.0.0.0', 6660), RequestHandler)
        server.auth_code = None
        server.access_token = None
        server.token_event = self.token_event
        server.serve_forever()

    def check_token_file(self):
        while not self.token_event.is_set():
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    expiration_time = token_data['expiration_time']
                    if time.time() < expiration_time:
                        self.access_token = token_data['access_token']
                        self.token_event.set()
            time.sleep(1)

    def request_new_access_token(self, auth_code):
        url = 'https://open.tiktokapis.com/v2/oauth/token/'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        payload = {
            'client_key': self.client_key,
            'client_secret': self.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        }
        response = requests.post(url, headers=headers, data=payload)

        if response.status_code != 200:
            raise Exception(f"Error getting access token: HTTP {response.status_code}")
        response_data = response.json()
        print(response_data)
        if 'access_token' not in response_data:
            raise Exception(f"Error getting access token: {response_data}")
        
        access_token = response_data['access_token']
        expires_in = response_data['expires_in']
        expiration_time = time.time() + expires_in

        with open(self.token_file, 'w') as f:
            json.dump({'access_token': access_token, 'expiration_time': expiration_time}, f)

        return access_token
    def calculate_chunk_count(self, video_size):
        """
        Calculate the number of chunks required to upload a video file to TikTok.
        
        :param video_size: Total size of the video in bytes.
        :return: Total number of chunks, chunk size, and last chunk size.
        """
        
        min_chunk_size = 5 * 1024 * 1024  # 5 MB
        max_chunk_size = 64 * 1024 * 1024  # 64 MB

        # Calculate chunk size
        # We'll set a preferred chunk size based on a fraction of the video size
        preferred_chunk_size = video_size // 10 if video_size >= 10 * min_chunk_size else min_chunk_size
        print(preferred_chunk_size)
        chunk_size = min(max(preferred_chunk_size, min_chunk_size), max_chunk_size)

        # Calculate total chunks
        total_chunks = math.ceil(video_size / chunk_size)

        # Calculate last chunk size to accommodate any trailing bytes
        last_chunk_size = video_size - (chunk_size * (total_chunks - 1))
        
        if total_chunks > 1 and last_chunk_size < min_chunk_size:
            # Distribute trailing bytes to other chunks if the last chunk is too small
            while last_chunk_size < min_chunk_size and total_chunks > 1:
                total_chunks -= 1
                chunk_size = video_size // total_chunks
                last_chunk_size = video_size - (chunk_size * (total_chunks - 1))
                if chunk_size > max_chunk_size:
                    chunk_size = max_chunk_size
                    total_chunks = math.ceil(video_size / chunk_size)
                    last_chunk_size = video_size - (chunk_size * (total_chunks - 1))
                    break

        return total_chunks, chunk_size, last_chunk_size

    def get_upload_url(self, access_token, video_size):
        url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        
        total_chunks, chunk_size, last_chunk_size = self.calculate_chunk_count(video_size)

        payload = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks
            }
        }
        print(payload)
        print(f"Video size: {video_size} bytes")
        print(f"Regular chunk size: {chunk_size} bytes")
        print(f"Last chunk size: {last_chunk_size} bytes")
        print(f"Total chunks: {total_chunks}")
        print(f"Payload for API request: {payload}")

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Full API response: {response.text}")
            raise Exception(f"Error getting upload URL: HTTP {response.status_code}, {response.text}")
        
        response_data = response.json()
        print(response_data)
        return response_data['data']['upload_url'], response_data['data']['publish_id']

    def upload_video(self, upload_url, video_path, video_size, total_chunks, chunk_size, last_chunk_size):
        with open(video_path, 'rb') as video_file:
            for chunk_index in range(total_chunks):
                is_last_chunk = chunk_index == total_chunks - 1
                current_chunk_size = last_chunk_size if is_last_chunk else chunk_size
                
                chunk_data = video_file.read(current_chunk_size)
                if not chunk_data:
                    break

                chunk_start = chunk_index * chunk_size
                chunk_end = chunk_start + len(chunk_data) - 1

                headers = {
                    'Content-Type': 'video/quicktime',
                    'Content-Length': str(len(chunk_data)),
                    'Content-Range': f'bytes {chunk_start}-{chunk_end}/{video_size}'
                }

                print(f"Uploading chunk {chunk_index + 1}/{total_chunks}: bytes {chunk_start}-{chunk_end}/{video_size}")
                response = requests.put(upload_url, headers=headers, data=chunk_data)

                if response.status_code not in (201, 206):
                    raise Exception(f"Error uploading video chunk: HTTP {response.status_code}, {response.text}")

                if response.status_code == 201:
                    print("Upload completed successfully.")
                    break

        if response.status_code != 201:
            raise Exception("Upload did not complete successfully.")

    def get_post_status(self, access_token, publish_id):
        status_url = f'https://open.tiktokapis.com/v2/post/publish/status/fetch/'
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        payload = {
            "publish_id": publish_id
        }
        while True:
            response = requests.post(status_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"Error fetching post status: HTTP {response.status_code}")
            status_response = response.json()
            status = status_response['data']['status']
            if status == 'PROCESSING_UPLOAD':
                time.sleep(3)
            else:
                return status_response

    def print_token_expiration(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                expiration_time = token_data['expiration_time']
                print("Access token will expire at:", time.ctime(expiration_time))
        else:
            print("Token file not found.")

