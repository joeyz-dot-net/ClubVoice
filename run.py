"""Project entrypoint to run the HLS streamer from repo root.

Usage:
  python run.py [args]

This sets up `src` on sys.path and invokes `src.hls_streamer.main()` so CLI and settings.ini work as expected.
"""
import os
import sys
import subprocess

# Ensure src/ is importable when running from repository root
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

def main():
    # Interactive menu: start streamer or run tools
    def list_devices():
        script_path = os.path.join(ROOT, 'tools', 'list_devices.py')
        if os.path.exists(script_path):
            print('\n[INFO] Running tools/list_devices.py\n')
            subprocess.run([sys.executable, script_path], check=False)
        else:
            print('\n[INFO] tools/list_devices.py not found; falling back to sounddevice query')
            try:
                import sounddevice as sd
                for i, d in enumerate(sd.query_devices()):
                    print(i, d.get('name'), 'max_in=', d.get('max_input_channels'), 'default_sr=', d.get('default_samplerate'))
            except Exception as e:
                print('[WARN] Failed to query devices via sounddevice:', e)

    while True:
        try:
            print('\n=== ClubVoice Launcher ===')
            print('1) Start streamer (default)')
            print('2) Tools - List audio devices')
            print('q) Quit')
            choice = input('Select an option [1]: ').strip().lower()
            if choice == '' or choice == '1':
                try:
                    from hls_streamer import main as streamer_main
                except Exception as e:
                    print('Failed to import hls_streamer from src/:', e)
                    raise
                streamer_main()
                break
            elif choice == '2':
                list_devices()
                input('\nPress Enter to return to menu...')
                continue
            elif choice in ('q', 'quit', '0'):
                print('Exiting.')
                break
            else:
                print('Unknown option:', choice)
        except KeyboardInterrupt:
            print('\nInterrupted; exiting.')
            break

if __name__ == '__main__':
    main()
