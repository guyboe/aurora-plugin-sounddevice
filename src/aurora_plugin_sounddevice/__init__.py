import sys
import enum
import queue
import pathlib
import logging
from typing import Union, Optional, List, Any

import ffmpeg
# import numpy as np
import sounddevice as sd

from .helpers import get_samplerate_func
from .config import Config
from .queues import Queues


class Plugin(Queues):

    NAME = "aurora_plugin_sounddevice"

    PLAY_QUEUE_SIZE = 10
    PLAY_BLOCK_SIZE = 1024

    def __init__(self, config: Config):
        self.config = config
        super().__init__()

    def listen(self):

        queue_ = queue.Queue()

        def callback(indata, frames, time, status):
            if status:
                logging.error("Status %s", status)
            queue_.put(bytes(indata))

        with sd.RawInputStream(
            device=self.config.input.device,
            samplerate=self.config.input.samplerate,
            blocksize=self.config.input.samplerate * 200 // 1000,
            dtype="int16",
            channels=1,
            callback=callback
        ):
            logging.info("Ready for listening audio with %s plugin", self.NAME)

            while data := queue_.get():
                result = self.publish(
                    data,
                    exchange=self.config.Queues.Exchange.Name.DETECT.value,
                    source=self.config.source
                )
                logging.debug("Got audio block %s", result["hash"])

    def play(self, filename: str):

        info = ffmpeg.probe(filename)
        streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
        if not streams:
            raise Exception("Audio streams not found")

        channels = streams[0]["channels"]
        samplerate = float(streams[0]["sample_rate"])

        queue_ = queue.Queue(maxsize=self.PLAY_QUEUE_SIZE)

        def callback(outdata, frames, time, status):
            assert frames == self.PLAY_BLOCK_SIZE
            if status.output_underflow:
                logging.error("Output underflow: increase blocksize?")
                raise sd.CallbackAbort
            assert not status
            try:
                data = queue_.get_nowait()
            except queue.Empty as e:
                logging.error("Buffer is empty: increase buffersize?")
                raise sd.CallbackAbort from e
            if len(data) != len(outdata):
                raise sd.CallbackAbort
            outdata[:] = data

        process = ffmpeg \
            .input(filename) \
            .output(
                "pipe:",
                format="f32le",
                acodec="pcm_f32le",
                ac=channels,
                ar=samplerate,
                loglevel="quiet",
            ).run_async(pipe_stdout=True)

        stream = sd.RawOutputStream(
            samplerate=samplerate,
            blocksize=self.PLAY_BLOCK_SIZE,
            device=self.config.output.device,
            channels=channels,
            dtype="float32",
            callback=callback
        )
        read_size = self.PLAY_BLOCK_SIZE * channels * stream.samplesize
        for _ in range(self.PLAY_QUEUE_SIZE):
            queue_.put_nowait(process.stdout.read(read_size))
        with stream:
            timeout = self.PLAY_BLOCK_SIZE * self.PLAY_QUEUE_SIZE / samplerate
            try:
                while True:
                    queue_.put(process.stdout.read(read_size), timeout=timeout)
            except queue.Full:
                pass
            except Exception as e:
                raise e

    def _play(self, body, message):
        filename = pathlib.Path(self.config.storage) / f"{message.headers['v-hash']}.wav"
        with open(filename, "wb") as f:
            f.write(body)
        self.play(filename)
        message.ack()
