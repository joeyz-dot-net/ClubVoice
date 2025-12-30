import sounddevice as sd

for i, d in enumerate(sd.query_devices()):
    print(i, d['name'], 'max_in=', d.get('max_input_channels'), 'default_sr=', d.get('default_samplerate'))
