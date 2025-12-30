"""
HLS streamer: capture PCM from an input device (e.g. VB-Cable), pipe to ffmpeg
to encode AAC and produce HLS segments, and serve them over HTTPS using Flask.

Requirements:
 - ffmpeg available (ffmpeg.exe provided in repo or on PATH)
 - Python packages: sounddevice, numpy, flask

Usage example:
  python -m src.hls_streamer --device-name "CABLE-B Output (VB-Audio Virtual Cable B)" \
      --sample-rate 48000 --channels 2 --hls-dir ./hls --ffmpeg ./ffmpeg.exe --cert cert.pem --key key.pem

Notes:
 - On Windows you may need to run as a user that can access the virtual audio device.
 - Generating a self-signed cert for local HTTPS testing:
     openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem

This script keeps things simple: it captures int16 PCM frames and writes them to
ffmpeg stdin. ffmpeg handles AAC encoding and HLS segmenting.
"""
from __future__ import annotations

import argparse
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from flask import Flask, send_from_directory
try:
    import soundcard as sc
except Exception:
    sc = None


def spawn_ffmpeg(ffmpeg_path: str, sample_rate: int, channels: int, bitrate: str, hls_dir: str, playlist_name: str = 'stream.m3u8'):
    os.makedirs(hls_dir, exist_ok=True)
    playlist_path = os.path.join(hls_dir, playlist_name)

    cmd = [
        ffmpeg_path,
        '-y',
        '-f', 's16le',
        '-ar', str(sample_rate),
        '-ac', str(channels),
        '-i', 'pipe:0',
        '-c:a', 'aac',
        '-b:a', bitrate,
        '-vn',
        '-f', 'hls',
        '-hls_time', '2',
        '-hls_list_size', '6',
        '-hls_flags', 'delete_segments+append_list+omit_endlist',
        '-fflags', 'nobuffer',
        '-flush_packets', '1',
        playlist_path,
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


class PCMWriter:
    def __init__(self, ffmpeg_proc: subprocess.Popen, sample_rate: int, channels: int, chunk_size: int = 512, gain: float = 1.0):
        self.proc = ffmpeg_proc
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.gain = gain
        self.q: queue.Queue[np.ndarray] = queue.Queue(maxsize=500)
        self.running = False
        self._thread = threading.Thread(target=self._writer_thread, daemon=True)
        # for debug: save first 10 seconds raw PCM
        self._debug_pcm = []
        self._debug_max_frames = sample_rate * channels * 10  # 10 seconds
        self._debug_saved = False

    def start(self):
        self.running = True
        self._thread.start()

    def stop(self):
        self.running = False
        self._thread.join(timeout=1.0)
        try:
            if self.proc and self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass

    def write(self, frames: np.ndarray):
        # debug: save raw PCM for first 10 seconds
        if not self._debug_saved:
            self._debug_pcm.append(frames.copy())
            total_frames = sum(x.shape[0] for x in self._debug_pcm)
            if total_frames >= self._debug_max_frames:
                import wave
                wav_path = 'test_capture.wav'
                with wave.open(wav_path, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join([x.astype(np.int16).tobytes() for x in self._debug_pcm]))
                print(f'[DEBUG] Saved first 10s raw PCM to {wav_path}')
                self._debug_saved = True
        try:
            self.q.put_nowait(frames)
        except queue.Full:
            # drop if full
            pass

    def _writer_thread(self):
        while self.running:
            try:
                frames = self.q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                if self.proc.poll() is not None:
                    # ffmpeg died
                    self.running = False
                    break
                # convert to float32 for gain processing
                arr = frames.astype(np.float32)
                if self.gain != 1.0:
                    arr = arr * float(self.gain)
                # clip to int16 range and convert
                arr = np.clip(arr, -32768.0, 32767.0).astype(np.int16)
                # write raw bytes
                self.proc.stdin.write(arr.tobytes())
                self.proc.stdin.flush()
            except Exception:
                break


def start_capture(device, sample_rate, channels, chunk_size, writer: PCMWriter):
    def callback(indata, frames, time_info, status):
        if status:
            print('Input status:', status, file=sys.stderr)
        # indata is shape (frames, channels)
        audio = indata.copy()
        # ensure int16
        if audio.dtype != np.int16:
            # sounddevice may deliver float32 in [-1,1]
            if np.issubdtype(audio.dtype, np.floating):
                audio = (audio * 32767.0).astype(np.int16)
            else:
                audio = audio.astype(np.int16)
        writer.write(audio)

    # Try to open InputStream, with fallbacks on channel count if PortAudio rejects requested channels
    attempt_order = [channels]
    # append common fallback of 1 channel
    if 1 not in attempt_order:
        attempt_order.append(1)
    # try device's reported max input channels
    try:
        info = sd.query_devices(device)
        max_in = int(info.get('max_input_channels', 0))
        if max_in > 0 and max_in not in attempt_order:
            attempt_order.append(max_in)
    except Exception:
        max_in = None

    last_err = None
    for ch in attempt_order:
        try:
            print(f'[DEBUG] Trying InputStream with device={device}, channels={ch}, samplerate={sample_rate}, blocksize={chunk_size}')
            stream = sd.InputStream(device=device, channels=ch, samplerate=sample_rate, dtype='int16', blocksize=chunk_size, callback=callback)
            stream.start()
            # report actual stream parameters
            try:
                actual_sr = getattr(stream, 'samplerate', None)
                actual_ch = getattr(stream, 'channels', ch)
                print(f'[DEBUG] Opened stream: samplerate={actual_sr}, channels={actual_ch}')
            except Exception:
                pass
            if ch != channels:
                print(f'[WARN] Opened device with channels={ch} (requested {channels})')
            return stream
        except Exception as e:
            print(f'[DEBUG] Failed to open InputStream with channels={ch}: {e}')
            last_err = e

    # final attempt: try default device
    try:
        print('[DEBUG] Trying default input device with 1 channel')
        stream = sd.InputStream(device=None, channels=1, samplerate=sample_rate, dtype='int16', blocksize=chunk_size, callback=callback)
        stream.start()
        return stream
    except Exception as e:
        print('[ERROR] All attempts to open InputStream failed')
        raise last_err or e


def start_capture_wasapi(device_name, sample_rate, channels, chunk_size, writer: PCMWriter):
    # Debug: 列出所有可用 speaker 和 loopback microphone
    print('[DEBUG] sc.all_speakers():')
    for s in sc.all_speakers():
        print('  ', s.name)
    print('[DEBUG] sc.all_microphones(include_loopback=True):')
    for m in sc.all_microphones(include_loopback=True):
        print('  ', m.name, '(loopback)' if getattr(m, 'isloopback', False) else '')
    """Capture system audio using WASAPI loopback via the soundcard library (auto-detect API)."""
    if sc is None:
        raise RuntimeError('soundcard library not available; install with `pip install soundcard`')

    # select speaker by name if provided
    speaker = None
    if device_name:
        for s in sc.all_speakers():
            try:
                if device_name.lower() in s.name.lower():
                    speaker = s
                    break
            except Exception:
                continue
    if speaker is None:
        speaker = sc.default_speaker()

    # Try new API: loopback_microphone
    microphone = None
    rec = None
    try:
        microphone = getattr(speaker, 'loopback_microphone', None)
        if callable(microphone):
            microphone = speaker.loopback_microphone()
            rec = microphone.recorder(samplerate=sample_rate, channels=channels)
        else:
            raise AttributeError
    except Exception:
        # Fallback: old API, get_microphone with include_loopback=True
        # Try to find a matching microphone device
        mic_name = None
        if device_name:
            for m in sc.all_microphones(include_loopback=True):
                try:
                    if device_name.lower() in m.name.lower() and m.isloopback:
                        mic_name = m.name
                        break
                except Exception:
                    continue
        if mic_name is None:
            # fallback to default speaker's loopback
            mic_name = sc.default_speaker().name
        microphone = sc.get_microphone(mic_name, include_loopback=True)
        rec = microphone.recorder(samplerate=sample_rate, channels=channels)

    def _loop():
        with rec:
            n = 0
            while True:
                frames = rec.record(numframes=chunk_size)
                # Debug: 打印采集数据基本信息
                if n < 10:
                    print(f'[DEBUG] frames dtype={frames.dtype}, shape={frames.shape}, min={frames.min()}, max={frames.max()}')
                    print(f'[DEBUG] first 10 samples: {frames.flatten()[:10]}')
                n += 1
                # soundcard returns float32 in [-1,1]
                if frames.dtype != np.int16:
                    frames_int16 = (frames * 32767.0).astype(np.int16)
                else:
                    frames_int16 = frames
                writer.write(frames_int16)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


def run_server(hls_dir: str, host: str, port: int, cert: str | None = None, key: str | None = None):
    import logging
    app = Flask('hls_server', static_folder=None)
    # reduce Werkzeug (access) logging to avoid console spam
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    @app.route('/<path:filename>')
    def static_file(filename):
        return send_from_directory(hls_dir, filename)

    @app.route('/')
    def index():
        # return built-in player HTML
        html = '''<!doctype html>
<html>
<head><meta charset="utf-8"><title>HLS Player</title></head>
<body>
<h3>HLS Test Player</h3>
<video id="video" controls autoplay style="width:80%;height:60%;background:#000"></video>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1"></script>
<script>
const video = document.getElementById('video');
const url = '/stream.m3u8';
if (Hls.isSupported()) {
  const hls = new Hls();
  hls.loadSource(url);
  hls.attachMedia(video);
  hls.on(Hls.Events.ERROR, function(e,data){console.warn('hls error', e, data)});
} else if (video.canPlayType('application/vnd.apple.mpegurl')) {
  video.src = url;
}
</script>
</body>
</html>'''
        return html

    @app.route('/player')
    def player():
        return index()

    if cert and key and os.path.exists(cert) and os.path.exists(key):
        ssl_context = (cert, key)
    else:
        ssl_context = None

    # allow cross-origin access for HLS segments (useful for local testing)
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Range,Accept'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
        return response

    app.run(host=host, port=port, ssl_context=ssl_context, threaded=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device-name', type=str, help='Partial device name to match VB-Cable')
    parser.add_argument('--device-id', type=int, help='Sounddevice device id (overrides name)')
    parser.add_argument('--wasapi', action='store_true', help='Use WASAPI loopback capture via soundcard')
    parser.add_argument('--sd-test', action='store_true', help='Test: use sounddevice to record 10s and save to test_sd.wav')
    parser.add_argument('--sample-rate', type=int, default=48000)
    parser.add_argument('--channels', type=int, default=2)
    parser.add_argument('--chunk-size', type=int, default=512)
    parser.add_argument('--gain', type=float, default=1.0, help='Apply gain multiplier to PCM before encoding')
    parser.add_argument('--hls-dir', type=str, default='hls')
    parser.add_argument('--ffmpeg', type=str, default=os.path.join(os.getcwd(), 'ffmpeg.exe'))
    parser.add_argument('--bitrate', type=str, default='128k')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--cert', type=str, help='Path to cert.pem for HTTPS')
    parser.add_argument('--key', type=str, help='Path to key.pem for HTTPS')

    args = parser.parse_args()
    if args.sd_test:
        import wave
        import numpy as np
        print('[SD-TEST] Querying devices...')
        devs = sd.query_devices()
        dev_idx = None
        if args.device_id is not None:
            dev_idx = args.device_id
        elif args.device_name:
            for i, d in enumerate(devs):
                if args.device_name.lower() in d['name'].lower():
                    dev_idx = i
                    break
        if dev_idx is None:
            print('[SD-TEST] Device not found. Available:')
            for i, d in enumerate(devs):
                print(i, d['name'])
            return
        print(f'[SD-TEST] Using device {dev_idx}: {devs[dev_idx]["name"]}')
        duration = 10
        print(f'[SD-TEST] Recording {duration}s...')
        rec = sd.rec(int(args.sample_rate * duration), samplerate=args.sample_rate, channels=args.channels, dtype='int16', device=dev_idx)
        sd.wait()
        wav_path = 'test_sd.wav'
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(args.channels)
            wf.setsampwidth(2)
            wf.setframerate(args.sample_rate)
            wf.writeframes(rec.tobytes())
        print(f'[SD-TEST] Saved {wav_path}')
        return

    # select device for sounddevice capture
    device = None
    if args.device_id is not None:
        device = args.device_id
    elif args.device_name:
        # for sounddevice mode, find device index
        devs = sd.query_devices()
        match = None
        for i, d in enumerate(devs):
            if args.device_name.lower() in d['name'].lower():
                match = i
                break
        if match is None:
            print('Device matching', args.device_name, 'not found. Available devices:')
            for i, d in enumerate(devs):
                print(i, d['name'])
            return
        device = match
    else:
        print('No device specified; using default input')

    # determine device channel capability and clamp channels if needed
    channels = args.channels
    sample_rate = args.sample_rate
    try:
        dev_info = sd.query_devices(device)
        max_in = int(dev_info.get('max_input_channels', 0))
        default_sr = dev_info.get('default_samplerate')
        if default_sr:
            try:
                default_sr = int(default_sr)
                if default_sr != args.sample_rate:
                    print(f"[WARN] Device default samplerate {default_sr} differs from requested {args.sample_rate}; using device default to avoid speed mismatch")
                    sample_rate = default_sr
            except Exception:
                pass
        if max_in <= 0:
            print(f'Warning: selected device has no input channels (max_input_channels={max_in})')
        elif channels > max_in:
            print(f'Warning: requested {channels} channels but device supports {max_in}; clamping to {max_in}')
            channels = max_in
    except Exception:
        # unable to query device info; proceed with requested channels and sample_rate
        pass

    # cleanup previous hls dir
    hls_dir = args.hls_dir
    if os.path.exists(hls_dir):
        # keep existing but remove playlist and segments to start fresh
        for f in os.listdir(hls_dir):
            if f.endswith('.ts') or f.endswith('.m3u8') or f.startswith('stream'):
                try:
                    os.remove(os.path.join(hls_dir, f))
                except Exception:
                    pass
    else:
        os.makedirs(hls_dir, exist_ok=True)

    ffmpeg_proc = spawn_ffmpeg(args.ffmpeg, sample_rate, channels, args.bitrate, hls_dir)
    writer = PCMWriter(ffmpeg_proc, sample_rate, channels, chunk_size=args.chunk_size, gain=args.gain)
    writer.start()

    # define shutdown before use
    stream = None
    def shutdown(signum, frame):
        print('Shutting down...')
        try:
            if stream:
                stream.stop()
        except Exception:
            pass
        writer.stop()
        try:
            ffmpeg_proc.terminate()
        except Exception:
            pass
        sys.exit(0)

    # start capture using sounddevice (force SD; WASAPI disabled)
    stream = start_capture(device, sample_rate, channels, args.chunk_size, writer)

    # run server in separate thread
    server_thread = threading.Thread(target=run_server, args=(hls_dir, args.host, args.port, args.cert, args.key), daemon=True)
    server_thread.start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print('HLS streaming started. Serving at {}:{} (hls dir: {})'.format(args.host, args.port, hls_dir))
    try:
        while True:
            time.sleep(1)
            # monitor ffmpeg stderr for errors
            if ffmpeg_proc and ffmpeg_proc.stderr and ffmpeg_proc.poll() is None:
                out = ffmpeg_proc.stderr.readline()
                if out:
                    try:
                        print(out.decode('utf-8', errors='ignore').strip())
                    except Exception:
                        pass
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == '__main__':
    main()
