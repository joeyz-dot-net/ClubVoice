import time
import sys
import numpy as np
import sounddevice as sd
try:
    import soundcard as sc
except Exception:
    sc = None

def list_input_devices():
    devs = sd.query_devices()
    print('Input devices:')
    for i, d in enumerate(devs):
        print(f"{i}: {d['name']}  max_in={d.get('max_input_channels')}  default_sr={d.get('default_samplerate')}")

def monitor_input(device_index, channels=1, blocksize=1024):
    info = sd.query_devices(device_index)
    sr = int(info.get('default_samplerate') or 48000)
    ch = channels
    print(f"\nMonitoring device {device_index}: {info['name']}  samplerate={sr}  channels={ch}. Press Ctrl+C to stop.")

    def callback(indata, frames, time_info, status):
        if status:
            print('\n[INPUT STATUS]', status, file=sys.stderr)
        arr = indata
        # convert floats [-1,1] to int16 range for level calc
        if np.issubdtype(arr.dtype, np.floating):
            arrf = (arr * 32767.0).astype(np.float32)
        else:
            arrf = arr.astype(np.float32)
        # compute per-channel rms and peak
        rms = np.sqrt(np.mean(arrf**2, axis=0))
        peak = np.max(np.abs(arrf), axis=0)
        # format
        parts = []
        for r, p in zip(rms, peak):
            parts.append(f"RMS={r:6.1f} PK={p:6.0f}")
        sys.stdout.write('\r' + ' | '.join(parts))
        sys.stdout.flush()

    try:
        with sd.InputStream(device=device_index, channels=ch, samplerate=sr, blocksize=blocksize, dtype='int16', callback=callback):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print('\nStopped.')
    except Exception as e:
        print('\nError opening device:', e)

def monitor_speaker_loopback(speaker_name=None, blocksize=1024):
    if sc is None:
        print('soundcard library not available; install with `pip install soundcard` to monitor speaker loopback')
        return
    # choose speaker
    speakers = list(sc.all_speakers())
    chosen = None
    if speaker_name:
        for s in speakers:
            if speaker_name.lower() in s.name.lower():
                chosen = s
                break
    if chosen is None:
        print('\nAvailable speakers:')
        for i, s in enumerate(speakers):
            print(f'{i}: {s.name}')
        idx = input('Select speaker index to monitor loopback [0]: ').strip()
        try:
            idx = int(idx) if idx != '' else 0
            chosen = speakers[idx]
        except Exception:
            print('Invalid selection')
            return

    print(f'Using speaker: {chosen.name} (loopback)')
    try:
        mic = getattr(chosen, 'loopback_microphone', None)
        if callable(mic):
            microphone = chosen.loopback_microphone()
        else:
            microphone = sc.get_microphone(chosen.name, include_loopback=True)
    except Exception as e:
        print('Failed to get loopback microphone:', e)
        return

    rec = microphone.recorder(samplerate=48000, channels=2)
    print('Monitoring speaker loopback. Press Ctrl+C to stop.')
    try:
        with rec:
            while True:
                frames = rec.record(numframes=blocksize)
                arrf = frames.astype(np.float32)
                rms = np.sqrt(np.mean(arrf**2, axis=0))
                peak = np.max(np.abs(arrf), axis=0)
                parts = []
                for r, p in zip(rms, peak):
                    parts.append(f"RMS={r:6.1f} PK={p:6.3f}")
                sys.stdout.write('\r' + ' | '.join(parts))
                sys.stdout.flush()
    except KeyboardInterrupt:
        print('\nStopped.')
    except Exception as e:
        print('\nError during loopback capture:', e)

def main():
    list_input_devices()
    print('\nOptions:')
    print('  [number] - monitor that input device real-time volume')
    print('  s        - monitor speaker loopback (system audio) if soundcard available')
    print('  q        - quit')
    while True:
        cmd = input('\nSelect option: ').strip().lower()
        if cmd == 'q' or cmd == 'quit':
            break
        if cmd == 's':
            monitor_speaker_loopback()
            continue
        try:
            idx = int(cmd)
            devs = sd.query_devices()
            if 0 <= idx < len(devs):
                max_in = int(devs[idx].get('max_input_channels') or 0)
                ch = 1 if max_in <= 0 else min(2, max_in)
                monitor_input(idx, channels=ch)
            else:
                print('Invalid device index')
        except ValueError:
            print('Unknown option')


if __name__ == '__main__':
    main()
