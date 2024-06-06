import os
import time
import logging
import subprocess
from audio_separator.separator import Separator
from moviepy.editor import *
from moviepy.config import change_settings
from dotenv import load_dotenv
load_dotenv()
change_settings({"FFMPEG_BINARY": "ffmpeg"})
options_codec = os.environ.get("codec")

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

        #separator.load_model(model_filename='UVR_MDXNET_KARA.onnx')

        time.sleep(10)

        try:
            #output_files = separator.separate(os.path.join(self.workdir, 'output/', vocal_one[0]))
            self.vocalaudio = os.path.join(
                self.workdir, 'output/', vocal_one[0])
            #os.remove(os.path.join(self.workdir, 'output/', vocal_one[0]))
            """ self.vocalaudio = os.path.join(
                self.workdir, 'output/', vocal_one[0]) """
        except Exception as e:
            # Handle the case where basename extraction fails
            logging.error(f"Error processing audio file: {e}")
            self.vocalaudio = vocal_one


    def patch(self):
        # Define input and output paths
        input_video_path = os.path.join(self.workdir, self.videofile)
        output_video_path = os.path.join(self.workdir, 'output', f'yt-vocals-{self.videofile}').replace(".mp4", ".mkv")
        
        # Load video clip
        video_clip = VideoFileClip(input_video_path)
        
        # Load new audio clip
        audio_clip = AudioFileClip(self.vocalaudio)
        
        # Replace the audio of the video clip with the new audio clip
        video_clip_with_new_audio = video_clip.set_audio(audio_clip)
        
        # Write the new video file with the replaced audio
        video_clip_with_new_audio.write_videofile(output_video_path, codec=options_codec, audio_codec="aac", temp_audiofile='temp-audio.m4a', remove_temp=True)

        # Close the clips
        video_clip.close()
        audio_clip.close()
        video_clip_with_new_audio.close()
        
        try:
            os.remove(self.vocalaudio)
        except Exception as e:
            print(e)

        return output_video_path.split('/')[-1]
