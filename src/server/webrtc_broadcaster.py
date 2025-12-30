"""Simple WebRTC broadcaster endpoint using aiortc.

This module provides a Flask blueprint that accepts an SDP offer (POST /webrtc-offer)
and returns an SDP answer. The server will attach an audio source (configurable)
using aiortc.MediaPlayer (ffmpeg) and send audio (Opus) to the connecting client.

Notes:
- Requires `aiortc` and its dependencies installed.
- On Windows you can use an ffmpeg WASAPI source string such as
  "-f wasapi -i default" or a file. Configure `WEBRTC_SOURCE` in environment
  or configuration to point to the ffmpeg input spec (see README).
"""
from __future__ import annotations

import os
import asyncio
from flask import Blueprint, request, jsonify, current_app
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer

bp = Blueprint('webrtc', __name__)


@bp.route('/webrtc-offer', methods=['POST'])
def offer():
    """Accept SDP offer JSON {sdp, type} and return SDP answer."""
    data = request.get_json()
    if not data or 'sdp' not in data or 'type' not in data:
        return jsonify({'error': 'invalid request'}), 400

    offer_sdp = data['sdp']
    offer_type = data['type']

    async def handle_offer():
        pc = RTCPeerConnection()

        # Choose media source from env or default to a local file placeholder
        src = os.environ.get('WEBRTC_SOURCE') or current_app.config.get('WEBRTC_SOURCE') or None
        if src:
            # MediaPlayer can accept file paths or ffmpeg input args string when prefixed with "ffmpeg:".
            # e.g. WEBRTC_SOURCE="ffmpeg:-f wasapi -i default"
            if src.startswith('ffmpeg:'):
                cmd = src[len('ffmpeg:'):].strip()
                player = MediaPlayer(cmd, format='lavfi') if cmd else None
            else:
                player = MediaPlayer(src)
        else:
            player = None

        if player and player.audio:
            pc.addTrack(player.audio)

        # set remote description
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type=offer_type))
        # create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # We do not keep pcs around in this simple scaffold; production should manage lifecycle
        return pc.localDescription.sdp, pc.localDescription.type

    loop = asyncio.new_event_loop()
    try:
        sdp, typ = loop.run_until_complete(handle_offer())
    finally:
        try:
            loop.close()
        except Exception:
            pass

    return jsonify({'sdp': sdp, 'type': typ})
