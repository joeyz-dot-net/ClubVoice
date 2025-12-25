from clubdeck import ClubdeckAudioProcessor

class ClubdeckIntegration:
    def __init__(self):
        self.processor = ClubdeckAudioProcessor()

    def start_processing(self):
        self.processor.start()

    def stop_processing(self):
        self.processor.stop()

    def process_audio(self, audio_data):
        return self.processor.process(audio_data)

    def set_parameters(self, params):
        self.processor.set_parameters(params)