import os
import time
import logging
import numpy as np
from audio_separator.separator import Separator
from moviepy.editor import *
from moviepy.config import change_settings
from scipy.io import wavfile
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from dotenv import load_dotenv

load_dotenv()
change_settings({"FFMPEG_BINARY": "ffmpeg"})
options_codec = os.environ.get("codec")

class dmcaf:
    def __init__(self, workdir, videofile, nonvocalaudio=None):
        self.workdir = workdir
        if nonvocalaudio != None:
            self.vocalaudio = nonvocalaudio
        else:
            self.vocalaudio = None
        self.videofile = videofile
        # Check if the output directory exists, if not, create it
        output_dir = os.path.join(self.workdir, 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def sepperate(self):
        moded_mdx_params = {"hop_length": 1024, "segment_size": 768, "overlap": 0.5, "batch_size": 8, "enable_denoise": True}
        # Initialize the Separator class (with optional configuration properties below)
        separator = Separator(log_level=logging.ERROR, output_format='FLAC',
                              output_single_stem='vocals', output_dir=os.path.join(self.workdir, 'output/'), mdx_params=moded_mdx_params)

        # Load a machine learning model (if unspecified, defaults to 'UVR-MDX-NET-Inst_HQ_3.onnx')
        separator.load_model(model_filename='Kim_Vocal_2.onnx')

        # Perform the separation on specific audio files without reloading the model
        vocal_one = separator.separate(os.path.join(self.workdir, self.videofile))

        time.sleep(10)

        try:
            self.vocalaudio = os.path.join(self.workdir, 'output/', vocal_one[0])
        except Exception as e:
            # Handle the case where basename extraction fails
            logging.error(f"Error processing audio file: {e}")
            self.vocalaudio = vocal_one

    def reinsert_silences(self, original_audio_path, separated_audio_path):
        # Read original and separated audio files
        original_audio = AudioSegment.from_file(original_audio_path)
        separated_audio = AudioSegment.from_file(separated_audio_path)

        # Detect non-silent segments in the original audio
        nonsilent_ranges = detect_nonsilent(original_audio, min_silence_len=1000, silence_thresh=-40)

        # Create an empty audio segment for the final output
        final_audio = AudioSegment.silent(duration=len(original_audio))

        # Overlay non-silent parts of the separated audio onto the final audio
        for start, end in nonsilent_ranges:
            segment = separated_audio[start:end]
            final_audio = final_audio.overlay(segment, position=start)

        # Export the final audio
        output_path = separated_audio_path.replace('.flac', '_with_silences.flac')
        final_audio.export(output_path, format='flac')
        
        return output_path

    def patch(self):
        # Define input and output paths
        input_video_path = os.path.join(self.workdir, self.videofile)
        output_video_path = os.path.join(self.workdir, 'output', f'yt-vocals-{self.videofile}').replace(".mp4", ".mkv")

        # Load video clip
        video_clip = VideoFileClip(input_video_path)

        # Reinsert silences into the vocal audio
        separated_audio_path = self.vocalaudio
        final_audio_path = self.reinsert_silences(input_video_path, separated_audio_path)

        # Load new audio clip with silences reinserted
        audio_clip = AudioFileClip(final_audio_path)

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

# Example usage:
# dmcaf_instance = dmcaf(workdir='path/to/workdir', videofile='video.mp4')
# dmcaf_instance.sepperate()
# output_video = dmcaf_instance.patch()