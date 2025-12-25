# Real-Time Voice Communication Application

This project is a real-time voice communication application that enables bidirectional audio communication between a browser and a server. The application utilizes WebRTC for peer-to-peer audio streaming and integrates with Clubdeck for audio processing.

## Features

- Bidirectional audio communication
- WebSocket-based signaling for WebRTC connections
- Audio processing handled by Clubdeck
- Simple user interface for initiating voice calls

## Project Structure

```
voice-communication-app
├── src
│   ├── main.py                # Entry point of the application
│   ├── server                  # Contains server-related code
│   ├── audio                   # Contains audio processing code
│   ├── webrtc                  # Contains WebRTC handling code
│   └── utils                   # Contains utility functions and configurations
├── static                      # Contains static files (HTML, JS)
├── tests                       # Contains unit tests
├── requirements.txt            # Project dependencies
└── pyproject.toml             # Project metadata and configuration
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd voice-communication-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start the server:
   ```
   python src/main.py
   ```

2. Open `static/index.html` in a web browser to access the user interface.

3. Follow the on-screen instructions to initiate voice communication.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.