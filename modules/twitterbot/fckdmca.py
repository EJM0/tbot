import os
import time
import logging
import subprocess
from audio_separator.separator import Separator
from moviepy.editor import *
from moviepy.config import change_settings
change_settings({"FFMPEG_BINARY": "ffmpeg"})


class dmcaf:
    def __init__(self, workdir, videofile):
        self.workdir = workdir
        self.videofile = videofile
        self.vocalaudio = None
        # Check if the output directory exists, if not, create it
        output_dir = os.path.join(self.workdir, 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def sepperate(self):
        # Initialize the Separator class (with optional configuration properties below)
        separator = Separator(log_level=logging.ERROR, output_format='FLAC',
                              output_single_stem='vocals', output_dir=os.path.join(self.workdir, 'output/'))

        # Load a machine learning model (if unspecified, defaults to 'UVR-MDX-NET-Inst_HQ_3.onnx')
        separator.load_model(model_filename='Kim_Vocal_2.onnx')

        # Perform the separation on specific audio files without reloading the model
        vocal_one = separator.separate(
            os.path.join(self.workdir, self.videofile))

        separator.load_model(model_filename='UVR_MDXNET_KARA.onnx')

        time.sleep(10)

        try:
            output_files = separator.separate(os.path.join(
                self.workdir, 'output/', vocal_one[0]))
            self.vocalaudio = os.path.join(
                self.workdir, 'output/', output_files[0])
        except Exception as e:
            # Handle the case where basename extraction fails
            logging.error(f"Error processing audio file: {e}")
            self.vocalaudio = vocal_one


    def patch(self):
        # Define input and output paths
        input_video_path = os.path.join(self.workdir, self.videofile)
        output_video_path = os.path.join(
            self.workdir, 'output', f'yt-vocals-{self.videofile}').replace(".mp4", ".mkv")

        # Execute ffmpeg command to copy the video and replace the audio
        process = subprocess.Popen(['ffmpeg', '-i', input_video_path, '-i', self.vocalaudio, '-c:v', 'copy', '-c:a', 'aac', '-strict',
                                   'experimental', '-map', '0:v:0', '-map', '1:a:0', output_video_path, '-y'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Print the output in real-time
        """ for line in process.stdout:
            print("FFmpeg output:", line, end="") """

        """ for line in process.stderr:
            print("FFmpeg error:", line, end="") """

        # Wait for the process to finish
        process.wait()
        time.sleep(2)
        # Remove the not needed audio file
        # os.remove(self.vocalaudio)

        return output_video_path.split('/')[-1]
