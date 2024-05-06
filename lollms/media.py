"""
Project: LoLLMs
Author: ParisNeo
Description: Media classes:
    - WebcamImageSender: is a captures images from the webcam and sends them to a SocketIO client.
    - MusicPlayer: is a MusicPlayer class that allows you to play music using pygame library.
License: Apache 2.0
"""
from lollms.utilities import PackageManager
from lollms.com import LoLLMsCom
from lollms.utilities import trace_exception, run_async
from ascii_colors import ASCIIColors
import platform
from functools import partial
import subprocess

import os
import threading

if not PackageManager.check_package_installed("cv2"):
    if platform.system() == "Darwin":
        os.system('brew install opencv')
    elif platform.system() == "Windows":
        os.system('pip install opencv-python')
    else:
        os.system('pip install opencv-python')
        # os.system('sudo apt-get update')
        # os.system('sudo apt-get install libgl1-mesa-glx python3-opencv -y')
        # os.system('pip install opencv-python')
try:
    import cv2
except:
    ASCIIColors.error("Couldn't install opencv!")


if not PackageManager.check_package_installed("scipy"):
    PackageManager.install_package("scipy")
    from scipy import signal
from scipy import signal

if not PackageManager.check_package_installed("matplotlib"):
    PackageManager.install_package("matplotlib")
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

if not PackageManager.check_package_installed("whisper"):
    PackageManager.install_package("openai-whisper")
    try:
        import conda.cli
        conda.cli.main("install", "conda-forge::ffmpeg", "-y")
    except:
        ASCIIColors.bright_red("Couldn't install ffmpeg. whisper won't work. Please install it manually")

import whisper

import socketio
from lollms.com import LoLLMsCom
try:
    if not PackageManager.check_package_installed("sounddevice"):
        # os.system("sudo apt-get install portaudio19-dev")
        PackageManager.install_package("sounddevice")
        PackageManager.install_package("wave")
except:
    # os.system("sudo apt-get install portaudio19-dev -y")
    PackageManager.install_package("sounddevice")
    PackageManager.install_package("wave")
try:
    import sounddevice as sd
    import wave
except:
    ASCIIColors.error("Couldn't load sound tools")

import time
import base64
import io
import socketio
from scipy.io.wavfile import write
from matplotlib import pyplot as plt
import numpy as np
from scipy.signal import spectrogram
from pathlib import Path
class AudioRecorder:
    def __init__(self, filename:Path, sio:socketio.Client=None, channels=1, sample_rate=16000, chunk_size=24678, silence_threshold=150.0, silence_duration=2, callback=None, lollmsCom:LoLLMsCom=None, build_spectrogram=False, model = "base", transcribe=False):
        self.sio = sio
        self.filename = Path(filename)
        self.filename.parent.mkdir(exist_ok=True, parents=True)
        self.channels = channels
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.callback = callback
        self.lollmsCom = lollmsCom
        self.buffer = []
        self.is_recording = False
        self.start_time = time.time()
        self.last_time = time.time()
        self.build_spectrogram = build_spectrogram
        self.transcribe = transcribe
        if transcribe:
            self.whisper = whisper.load_model(model)


    def audio_callback(self, indata, frames, time_, status):
        volume_norm = np.linalg.norm(indata)*10
        # if volume_norm > self.silence_threshold:
        #     self.last_sound_time = time.time()
        #     if not self.is_recording:
        #         self.is_recording = True
        #         self.start_time = time.time()
        if self.is_recording:
            self.buffer = np.append(self.buffer, indata.copy())
            if self.build_spectrogram:
                if (time.time() - self.last_time) > self.silence_duration:
                    self.update_spectrogram()

    def start_recording(self):
        try:
            self.is_recording = True
            self.buffer = np.array([], dtype=np.float32)
            self.audio_stream = sd.InputStream(callback=self.audio_callback, channels=self.channels, samplerate=self.sample_rate)
            self.audio_stream.start()
        except Exception as ex:
            self.lollmsCom.InfoMessage("Couldn't start recording.\nMake sure your input device is connected and operational")
            trace_exception(ex)
            
    def stop_recording(self):
        self.is_recording = False
        self.audio_stream.stop()
        self.audio_stream.close()
        write(self.filename, self.sample_rate, self.buffer)
        self.lollmsCom.info(f"Saved to {self.filename}")

        if self.transcribe:
            self.lollmsCom.info(f"Transcribing ... ")
            result = self.whisper.transcribe(str(self.filename))
            transcription_fn = str(self.filename)+".txt"
            with open(transcription_fn, "w", encoding="utf-8") as f:
                f.write(result["text"])
            self.lollmsCom.info(f"File saved to {transcription_fn}")
            if self.sio:
                run_async(partial(self.sio.emit,'transcript', result["text"]))
            return {"text":result["text"], "audio":transcription_fn}
        else:
            return {"text":""}


    def update_spectrogram(self):
        f, t, Sxx = spectrogram(self.buffer[-30*self.sample_rate:], self.sample_rate)
        plt.pcolormesh(t, f, 10 * np.log10(Sxx))
        # Convert plot to base64 image
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        if self.sio:
            run_async(partial(self.sio.emit,'update_spectrogram', img_base64))
        self.last_spectrogram_update = time.perf_counter()
        plt.clf()

class WebcamImageSender:
    """
    Class for capturing images from the webcam and sending them to a SocketIO client.
    """

    def __init__(self, sio:socketio, lollmsCom:LoLLMsCom=None):
        """
        Initializes the WebcamImageSender class.

        Args:
            socketio (socketio.Client): The SocketIO client object.
        """
        self.sio = sio
        self.last_image = None
        self.last_change_time = None
        self.capture_thread = None
        self.is_running = False
        self.lollmsCom = lollmsCom

    def start_capture(self):
        """
        Starts capturing images from the webcam in a separate thread.
        """
        self.is_running = True
        self.capture_thread = threading.Thread(target=self.capture_image)
        self.capture_thread.start()

    def stop_capture(self):
        """
        Stops capturing images from the webcam.
        """
        self.is_running = False
        self.capture_thread.join()

    def capture_image(self):
        """
        Captures images from the webcam, checks if the image content has changed, and sends the image to the client if it remains the same for 3 seconds.
        """
        try:
            cap = cv2.VideoCapture(0)

            while self.is_running:
                ret, frame = cap.read()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if self.last_image is None or self.image_difference(gray) > 2:
                    self.last_image = gray
                    self.last_change_time = time.time()

                _, buffer = cv2.imencode('.jpg', frame)
                image_base64 = base64.b64encode(buffer)
                if self.sio:
                    run_async(partial(self.sio.emit,"video_stream_image", image_base64.decode('utf-8')))

            cap.release()
        except Exception as ex:
            self.lollmsCom.error("Couldn't start webcam")
            trace_exception(ex)

    def image_difference(self, image):
        """
        Calculates the difference between two images using the absolute difference method.

        Args:
            image (numpy.ndarray): The current image.

        Returns:
            int: The sum of pixel intensities representing the difference between the current image and the last image.
        """
        if self.last_image is None:
            return 0

        diff = cv2.absdiff(image, self.last_image)
        diff_sum = diff.sum()

        return diff_sum

class MusicPlayer(threading.Thread):
    """
    MusicPlayer class for playing music using pygame library.

    Attributes:
    - file_path (str): The path of the music file to be played.
    - paused (bool): Flag to indicate if the music is paused.
    - stopped (bool): Flag to indicate if the music is stopped.
    """

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.paused = False
        self.stopped = False

    def run(self):
        """
        The main function that runs in a separate thread to play the music.
        """
        if not PackageManager.check_package_installed("pygame"):
            PackageManager.install_package("pygame")
        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(self.file_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy() and not self.stopped:
            if self.paused:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

    def pause(self):
        """
        Pauses the music.
        """
        self.paused = True

    def resume(self):
        """
        Resumes the paused music.
        """
        self.paused = False

    def stop(self):
        """
        Stops the music.
        """
        import pygame
        self.stopped = True
        pygame.mixer.music.stop()


class RealTimeTranscription:
    def __init__(self, callback):
        if not PackageManager.check_package_installed('pyaudio'):
            try:
                import conda.cli
                conda.cli.main("install", "anaconda::pyaudio", "-y")
            except:
                ASCIIColors.bright_red("Couldn't install pyaudio. whisper won't work. Please install it manually")
        import pyaudio
        # Initialize Whisper ASR
        print("Loading whisper ...", end="")
        self.whisper = whisper.load_model("base")
        print("ok")

        # Set up PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)

        # Set the callback
        self.callback = callback

    def start(self):
        import torch
        # Start the stream
        self.stream.start_stream()

        try:
            while True:
                # Read a chunk of audio data
                data = self.stream.read(1024)

                # Convert bytes to numpy array
                data_np = np.frombuffer(data, dtype=np.int16)
                # Convert numpy array to float tensor
                data_tensor = torch.tensor(data_np).float()
                # Send the chunk to Whisper for transcription
                result = self.whisper.transcribe(data_tensor)
                
                # If the result is not empty, call the callback
                if result:
                    self.callback(result["text"])
        except KeyboardInterrupt:
            # If the user hits Ctrl+C, stop the stream
            self.stop()

    def stop(self):
        # Stop the stream and clean up
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()