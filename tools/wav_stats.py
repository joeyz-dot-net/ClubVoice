import wave
import numpy as np
import os

files = ['test_capture.wav','test_sd.wav']
for f in files:
    print('---', f, '---')
    if not os.path.exists(f):
        print('MISSING:', f)
        continue
    try:
        w = wave.open(f, 'rb')
    except Exception as e:
        print('ERROR opening', f, e)
        continue
    n = w.getnframes()
    ch = w.getnchannels()
    sr = w.getframerate()
    data = w.readframes(n)
    arr = np.frombuffer(data, dtype=np.int16)
    if ch > 1:
        try:
            arr = arr.reshape(-1, ch)
        except Exception as e:
            print('reshape error:', e)
    rms = np.sqrt(np.mean(arr.astype(np.float32)**2))
    peak = np.max(np.abs(arr))
    print(f'frames={n}, channels={ch}, sr={sr}, rms={rms:.2f}, peak={peak}')
    # print first 40 samples flattened
    flat = arr.flatten()
    print('first 40 samples (flattened):', flat[:40])
    w.close()
print('\nDone.')
