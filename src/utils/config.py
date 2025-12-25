# Configuration settings for the voice communication application

SERVER_URL = "ws://localhost:8000"  # WebSocket server URL
AUDIO_SAMPLE_RATE = 44100  # Sample rate for audio processing
AUDIO_CHANNELS = 1  # Number of audio channels (1 for mono, 2 for stereo)
AUDIO_BITRATE = 128000  # Bitrate for audio encoding in bits per second

# Timeout settings
SIGNALING_TIMEOUT = 30  # Timeout for signaling responses in seconds

# Logging settings
LOG_LEVEL = "INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)