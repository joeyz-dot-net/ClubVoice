import wave
import numpy as np
import os
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False

files = ['test_capture.wav','test_sd.wav']
for f in files:
    print('---', f, '---')
    if not os.path.exists(f):
        print('MISSING:', f)
        continue
    w = wave.open(f,'rb')
    n = w.getnframes(); ch = w.getnchannels(); sr = w.getframerate()
    data = w.readframes(n)
    arr = np.frombuffer(data, dtype=np.int16)
    if ch > 1:
        arr = arr.reshape(-1, ch)
        mono = arr.mean(axis=1).astype(np.int16)
    else:
        mono = arr
    # Spectrogram (if matplotlib available)
    spec_path = None
    if HAVE_MPL:
        plt.figure(figsize=(10,4))
        Pxx, freqs, bins, im = plt.specgram(mono, NFFT=2048, Fs=sr, noverlap=1024, cmap='magma')
        plt.xlabel('Time [s]')
        plt.ylabel('Frequency [Hz]')
        plt.colorbar(label='Intensity dB')
        spec_path = f.replace('.wav','_spectrogram.png')
        plt.title(f)
        plt.tight_layout()
        plt.savefig(spec_path)
        plt.close()
    # Average power spectrum
    fft = np.abs(np.fft.rfft(mono * (1.0/32768.0)))
    freqs = np.fft.rfftfreq(len(mono), 1.0/sr)
    avg = fft
    # Find top peaks
    idx = np.argsort(avg)[-10:][::-1]
    top = [(freqs[i], avg[i]) for i in idx]
    print('Top frequency peaks (Hz, magnitude):')
    for fr, mag in top[:8]:
        print(f'  {fr:.1f} Hz -> {mag:.6f}')
    # Optionally save average spectrum plot
    sp_path = None
    if HAVE_MPL:
        plt.figure(figsize=(8,4))
        plt.semilogy(freqs, avg + 1e-20)
        plt.xlabel('Frequency [Hz]')
        plt.ylabel('Magnitude')
        plt.xlim(0, sr/2)
        plt.title(f + ' average spectrum')
        sp_path = f.replace('.wav','_spectrum.png')
        plt.tight_layout()
        plt.savefig(sp_path)
        plt.close()
    print('Saved:', spec_path, sp_path)
print('Done')
