import os
import time
from .utils import console

class MediaTools:

    def __init__(self, stage2):
        self.s2 = stage2

    def take_screenshot(self, output_path: str=None):
        if not output_path:
            output_path = f'screenshot_{int(time.time())}.png'
        console.print('[info]Capturing screen...')
        self.s2.session.send_command('screencap -p')
        try:
            with open(output_path, 'wb') as f:
                while True:
                    chunk = self.s2.session.socket.recv(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            console.print(f'[success]Screenshot saved to {output_path}[/]')
        except Exception as e:
            console.print(f'[error]Screenshot failed: {e}[/]')

    def stream_screen_record(self, duration: int=10, output_path: str='capture.mp4'):
        console.print(f'[info]Recording screen for {duration}s...')
        self.s2.session.send_command(f'screenrecord --time-limit {duration} --output-format h264 -')
        try:
            with open(output_path, 'wb') as f:
                while True:
                    chunk = self.s2.session.socket.recv(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            console.print(f'[success]Recording saved to {output_path}[/]')
        except Exception as e:
            console.print(f'[error]Recording failed: {e}[/]')