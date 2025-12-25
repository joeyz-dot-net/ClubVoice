/**
 * Voice Communication Client
 * 浏览器端音频采集与播放
 */

class VoiceClient {
    constructor() {
        // Socket.IO
        this.socket = null;
        this.clientId = null;

        // 音频上下文
        this.audioContext = null;
        this.mediaStream = null;
        this.mediaStreamSource = null;
        this.scriptProcessor = null;

        // 播放缓冲
        this.playbackQueue = [];
        this.isPlaying = false;

        // 状态
        this.isConnected = false;
        this.isMicActive = false;

        // 配置 - 48kHz 立体声 128kbps
        this.sampleRate = 48000;
        this.channels = 2;  // 立体声
        this.bufferSize = 2048;  // 减小缓冲区降低延迟
        
        // 噪声门限
        this.noiseGate = 0.01;  // 低于此值静音
        this.noiseGateEnabled = true;
        
        // 平滑播放
        this.nextPlayTime = 0;
        this.playbackLatency = 0.05; // 50ms 播放缓冲

        // UI 元素
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        this.clientIdSpan = document.getElementById('clientId');
        this.micButton = document.getElementById('micButton');
        this.micVolumeBar = document.getElementById('micVolumeBar');
        this.micLevel = document.getElementById('micLevel');
        this.speakerVolumeBar = document.getElementById('speakerVolumeBar');
        this.speakerLevel = document.getElementById('speakerLevel');
        this.errorMessage = document.getElementById('errorMessage');

        // 绑定事件
        this.micButton.addEventListener('click', () => this.toggleMic());

        // 初始化连接
        this.initSocket();
    }

    initSocket() {
        this.socket = io({
            transports: ['websocket', 'polling']
        });

        this.socket.on('connect', () => {
            console.log('已连接到服务器');
        });

        this.socket.on('connected', (data) => {
            this.clientId = data.client_id;
            this.isConnected = true;
            this.updateConnectionStatus(true);
            console.log('客户端 ID:', this.clientId);
        });

        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionStatus(false);
            console.log('与服务器断开连接');
        });

        this.socket.on('audio_from_clubdeck', (data) => {
            this.handleIncomingAudio(data);
        });

        this.socket.on('connect_error', (error) => {
            console.error('连接错误:', error);
            this.showError('无法连接到服务器');
        });
    }

    updateConnectionStatus(connected) {
        if (connected) {
            this.statusDot.classList.add('connected');
            this.statusText.textContent = '已连接';
            this.clientIdSpan.textContent = `ID: ${this.clientId.slice(0, 8)}...`;
        } else {
            this.statusDot.classList.remove('connected');
            this.statusText.textContent = '未连接';
            this.clientIdSpan.textContent = '';
        }
    }

    async toggleMic() {
        if (this.isMicActive) {
            this.stopMic();
        } else {
            await this.startMic();
        }
    }

    async startMic() {
        try {
            // 请求麦克风权限 - 立体声
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: this.sampleRate,
                    channelCount: this.channels
                }
            });

            // 创建音频上下文
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });

            // 创建媒体流源
            this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.mediaStream);

            // 创建脚本处理器 - 立体声输入输出
            this.scriptProcessor = this.audioContext.createScriptProcessor(this.bufferSize, this.channels, this.channels);

            this.scriptProcessor.onaudioprocess = (event) => {
                if (!this.isMicActive) return;

                // 获取立体声数据
                const leftChannel = event.inputBuffer.getChannelData(0);
                const rightChannel = this.channels > 1 && event.inputBuffer.numberOfChannels > 1 
                    ? event.inputBuffer.getChannelData(1) 
                    : leftChannel;
                
                // 计算音量
                const volume = this.calculateVolume(leftChannel);
                this.updateMicVolume(volume);
                
                // 噪声门限 - 音量太低时不发送
                if (this.noiseGateEnabled && volume < 2) {
                    return;  // 静音状态不发送
                }

                // 交织立体声数据并转换为 Int16
                const int16Data = this.float32StereoToInt16(leftChannel, rightChannel);
                const base64Data = this.arrayBufferToBase64(int16Data.buffer);

                this.socket.emit('audio_data', {
                    audio: base64Data,
                    channels: this.channels
                });
            };

            // 连接节点
            this.mediaStreamSource.connect(this.scriptProcessor);
            this.scriptProcessor.connect(this.audioContext.destination);

            this.isMicActive = true;
            this.micButton.classList.add('active');
            console.log('麦克风已开启');

        } catch (error) {
            console.error('无法访问麦克风:', error);
            this.showError('无法访问麦克风，请检查权限设置');
        }
    }

    stopMic() {
        if (this.scriptProcessor) {
            this.scriptProcessor.disconnect();
            this.scriptProcessor = null;
        }

        if (this.mediaStreamSource) {
            this.mediaStreamSource.disconnect();
            this.mediaStreamSource = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        this.isMicActive = false;
        this.micButton.classList.remove('active');
        this.updateMicVolume(0);
        console.log('麦克风已关闭');
    }

    handleIncomingAudio(data) {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: data.sample_rate || this.sampleRate
            });
        }

        try {
            // 解码 base64 立体声数据
            const int16Data = this.base64ToInt16Array(data.audio);
            const channels = data.channels || this.channels;
            const { left, right } = this.int16StereoToFloat32(int16Data, channels);

            // 更新音量指示器
            const volume = this.calculateVolume(left);
            this.updateSpeakerVolume(volume);

            // 播放立体声音频
            this.playAudioStereo(left, right);

        } catch (error) {
            console.error('处理接收音频失败:', error);
        }
    }

    playAudioStereo(leftData, rightData) {
        if (!this.audioContext) return;

        const buffer = this.audioContext.createBuffer(2, leftData.length, this.audioContext.sampleRate);
        buffer.getChannelData(0).set(leftData);
        buffer.getChannelData(1).set(rightData);

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        
        // 使用 GainNode 平滑音量变化，减少爆音
        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = 1.0;
        source.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        // 平滑调度播放时间
        const currentTime = this.audioContext.currentTime;
        const bufferDuration = buffer.duration;
        
        if (this.nextPlayTime < currentTime) {
            this.nextPlayTime = currentTime + this.playbackLatency;
        }
        
        source.start(this.nextPlayTime);
        this.nextPlayTime += bufferDuration;
    }

    // 工具函数
    float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return int16Array;
    }

    // 立体声 float32 转交织 int16
    float32StereoToInt16(leftChannel, rightChannel) {
        const length = leftChannel.length;
        const int16Array = new Int16Array(length * 2);  // 交织立体声
        for (let i = 0; i < length; i++) {
            const l = Math.max(-1, Math.min(1, leftChannel[i]));
            const r = Math.max(-1, Math.min(1, rightChannel[i]));
            int16Array[i * 2] = l < 0 ? l * 0x8000 : l * 0x7FFF;
            int16Array[i * 2 + 1] = r < 0 ? r * 0x8000 : r * 0x7FFF;
        }
        return int16Array;
    }

    // 交织 int16 转立体声 float32
    int16StereoToFloat32(int16Array, channels) {
        if (channels === 1) {
            const float32Array = new Float32Array(int16Array.length);
            for (let i = 0; i < int16Array.length; i++) {
                float32Array[i] = int16Array[i] / 0x8000;
            }
            return { left: float32Array, right: float32Array };
        }
        
        const length = int16Array.length / 2;
        const left = new Float32Array(length);
        const right = new Float32Array(length);
        for (let i = 0; i < length; i++) {
            left[i] = int16Array[i * 2] / 0x8000;
            right[i] = int16Array[i * 2 + 1] / 0x8000;
        }
        return { left, right };
    }

    int16ToFloat32(int16Array) {
        const float32Array = new Float32Array(int16Array.length);
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 0x8000;
        }
        return float32Array;
    }

    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    base64ToInt16Array(base64) {
        const binaryString = atob(base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return new Int16Array(bytes.buffer);
    }

    calculateVolume(audioData) {
        let sum = 0;
        for (let i = 0; i < audioData.length; i++) {
            sum += audioData[i] * audioData[i];
        }
        const rms = Math.sqrt(sum / audioData.length);
        return Math.min(100, Math.round(rms * 300));
    }

    updateMicVolume(volume) {
        this.micVolumeBar.style.width = volume + '%';
        this.micLevel.textContent = volume + '%';
    }

    updateSpeakerVolume(volume) {
        this.speakerVolumeBar.style.width = volume + '%';
        this.speakerLevel.textContent = volume + '%';
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        setTimeout(() => {
            this.errorMessage.style.display = 'none';
        }, 5000);
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.voiceClient = new VoiceClient();
});