import unittest
from src.audio.processor import AudioProcessor

class TestAudioProcessor(unittest.TestCase):

    def setUp(self):
        self.audio_processor = AudioProcessor()

    def test_audio_encoding(self):
        input_audio = b'sample audio data'
        encoded_audio = self.audio_processor.encode(input_audio)
        self.assertIsNotNone(encoded_audio)
        self.assertNotEqual(input_audio, encoded_audio)

    def test_audio_decoding(self):
        input_audio = b'sample audio data'
        encoded_audio = self.audio_processor.encode(input_audio)
        decoded_audio = self.audio_processor.decode(encoded_audio)
        self.assertEqual(input_audio, decoded_audio)

    def test_audio_processing(self):
        input_audio = b'sample audio data'
        processed_audio = self.audio_processor.process(input_audio)
        self.assertIsNotNone(processed_audio)

if __name__ == '__main__':
    unittest.main()