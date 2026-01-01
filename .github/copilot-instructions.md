# ClubVoice - AI Coding Agent Instructions

## Project Overview

**ClubVoice** is a real-time voice communication bridge enabling web browsers to communicate with Clubdeck rooms through VB-Cable virtual audio devices. The system uses WebSocket (Socket.IO) for bidirectional audio streaming between browser clients and a Python Flask server that interfaces with virtual audio cables.

## Architecture & Audio Flow

```
Browser <--Socket.IO--> Python Server <--VB-Cable--> Clubdeck
(Web Audio)            (sounddevice)      (Virtual Audio)
```

### Key Components

1. **Flask Server** ([src/server/app.py](src/server/app.py)) - HTTP + Socket.IO server hosting static files
2. **WebSocket Handler** ([src/server/websocket_handler.py](src/server/websocket_handler.py)) - Manages client connections, implements server-side audio ducking (reduces received volume when mic is active)
3. **VB-Cable Bridge** ([src/audio/vb_cable_bridge.py](src/audio/vb_cable_bridge.py)) - Single input/output architecture receives Clubdeck+MPV pre-mixed audio and sends browser audio back
4. **Device Manager** ([src/audio/device_manager.py](src/audio/device_manager.py)) - Interactive CLI for selecting VB-Cable devices with Rich UI, auto-detects VoiceMeeter/Hi-Fi Cable/VB-Cable devices
5. **Audio Processor** ([src/audio/processor.py](src/audio/processor.py)) - Noise gate, high-pass filter (100Hz cutoff), numpy/base64 conversions
6. **Bootstrap** ([src/bootstrap.py](src/bootstrap.py)) - Startup wizard with device selection and configuration summary
7. **Web Client** ([static/js/client.js](static/js/client.js)) - Web Audio API for mic capture, AudioBufferSourceNode for smooth playback with queuing

### Audio Pipeline Details

- **Sampling**: 48kHz stereo (int16) throughout entire pipeline
- **Browser**: Web Audio API → ScriptProcessor (2048 samples) → Socket.IO binary
- **Server**: Receives browser audio → VB-Cable output device (to Clubdeck mic input)
- **Server**: VB-Cable input device (from Clubdeck+MPV mixed) → Resampling if needed → Socket.IO → Browser
- **Latency optimization**: Small buffers (512 frames Python, 2048 browser), 50ms playback buffer
- **Ducking**: Server-side volume reduction (15%) when browser mic exceeds amplitude threshold (100), smooth transitions (0.08/frame)

## Critical Workflows

### Development Run
```powershell
python run.py  # Launches interactive device selector, then starts server on port 5000
```

### Build & Deploy (PyInstaller)
Tasks in `.vscode/tasks.json` handle the full build pipeline:
- **Full Build** (default): Clean → pyinstaller → copy config.ini → backup old version → deploy to `\\b560\code\voice-communication-app`
- **Build EXE**: Same as Full Build but without cleaning
- **Run App**: Direct Python execution for debugging
- **Run EXE**: Execute built executable from dist/

Build configuration in [ClubVoice.spec](ClubVoice.spec):
- Entry point: run.py
- Bundled: static/ folder, config.ini
- Hidden imports: engineio.async_drivers.threading, rich modules
- Console mode enabled (shows CLI device selector)

### Hardware Setup Requirements

**Dual VB-Cable isolation** (see [DUAL_CABLE_SETUP.md](DUAL_CABLE_SETUP.md)):
- VB-Cable A: Python ↔ Clubdeck communication
- Hi-Fi Cable (or VB-Cable B): Browser ↔ Python communication
- Clubdeck must route: Mic Input = Cable A Output, Speaker Output = Cable A Input
- This architecture eliminates audio feedback loops in full-duplex mode

**Simplified mixing architecture** (see [MPV_MUSIC_SETUP.md](MPV_MUSIC_SETUP.md)):
- Clubdeck performs hardware mixing of room audio + MPV music
- Python server receives pre-mixed input, no mixing logic needed
- MPV outputs to same Hi-Fi Cable Input that Clubdeck uses

## Project-Specific Conventions

### Configuration Management
- [config.ini](../config.ini): Server host/port, duplex mode ('half' = listen-only, 'full' = bidirectional), MPV pipe settings, mixing mode
- [src/config/settings.py](../src/config/settings.py): Dataclasses for AudioConfig, ServerConfig with defaults
- Device IDs and sample rates configured at runtime via Bootstrap CLI, not persisted

### Audio Processing Patterns
- **Resampling**: Custom linear interpolation in `VBCableBridge._resample()` - handles mismatched device sample rates
- **Channel conversion**: Mono→Stereo (duplicate), Stereo→Mono (average) in `_convert_channels()`
- **Queue management**: 200-frame max queues for input/output to prevent memory bloat
- **Smooth playback**: Browser maintains `nextPlayTime` scheduling, 50ms latency buffer
- **Noise gate**: Client-side threshold 0.01, server-side RMS threshold 150 (int16 range)

### Threading Model
- Main thread: Flask-SocketIO event loop (eventlet worker)
- Audio input thread: `VBCableBridge._input_stream_callback()` - reads from VB-Cable
- Audio output thread: `VBCableBridge._output_stream_callback()` - writes to VB-Cable  
- Forward thread: `WebSocketHandler._forward_audio_to_clients()` - socket broadcasts

### Error Handling & User Experience
- [run.py](run.py): Top-level exception handler with "Press Enter to exit" on errors
- Rich console: Color-coded device listings (cyan=VoiceMeeter, green=Hi-Fi, yellow=VB-Cable)
- Recommended devices: Auto-selects first VoiceMeeter/Hi-Fi/VB-Cable Output for input, Input for output
- Bootstrap displays full config summary before starting server
- **Cleanup on exit**: Automatically cleans PyInstaller temp directories (`_MEI*` in `%TEMP%`) on program exit

## Common Tasks

### Adding New Audio Processing
1. Add method to `AudioProcessor` class (maintain numpy int16 arrays)
2. Call from `VBCableBridge` resampling/conversion pipeline OR `WebSocketHandler` browser audio handler
3. Test with `python run.py` and monitor console amplitude logs

### Modifying Device Detection
1. Edit `DeviceManager.get_vb_cable_devices()` - matches 'CABLE' or 'VB-AUDIO' in device name (case-insensitive)
2. Update `_find_best_device()` scoring: VoiceMeeter B2 (100), B1 (80), Hi-Fi (70), VB-Cable (60)
3. Rich table formatting in `display_devices()` - color codes and device type labels

### Changing Audio Parameters
- Sample rate/channels: Modify `AudioConfig` defaults in [src/config/settings.py](src/config/settings.py#L22-L33)
- Buffer sizes: `chunk_size` in AudioConfig, `bufferSize` in [client.js](static/js/client.js#L30)
- Ducking behavior: Adjust `ducking_volume`/`ducking_threshold` in [websocket_handler.py](src/server/websocket_handler.py#L24-L30)

### Testing
- [tests/test_audio.py](tests/test_audio.py): AudioProcessor unit tests
- [tests/test_websocket.py](tests/test_websocket.py): Socket.IO mock tests
- [test_16ch.py](test_16ch.py): 16-channel device testing script
- Debug page: [static/debug.html](static/debug.html) - additional logging and controls

## Integration Points

- **Socket.IO events**: `connect`, `disconnect`, `audio_data` (browser→server), `play_audio` (server→browser), `get_config`
- **sounddevice**: Direct numpy array I/O with VB-Cable devices, callback-based streaming
- **PyInstaller**: Bundles Python + static files into single EXE, hidden imports critical for Flask-SocketIO/Rich
- **MPV**: Named pipe integration for music ducking (volume reduction when voice active), see `config.mpv` settings

## Important Notes

- **Never use subprocess or os.system for audio routing** - all audio flows through sounddevice streams
- **Avoid Python-side mixing** - current architecture relies on Clubdeck hardware mixing
- **Thread safety**: Use locks when modifying shared state (e.g., ducking_lock in WebSocketHandler)
- **Base64 encoding**: Browser sends/receives audio as base64 strings over Socket.IO, converted to numpy arrays server-side
- **Device ID persistence**: Not saved - user must select devices on each startup (by design)
- **PyInstaller temp cleanup**: Program automatically cleans `_MEI*` directories in `%TEMP%` on exit (see [src/utils/cleanup.py](src/utils/cleanup.py))
