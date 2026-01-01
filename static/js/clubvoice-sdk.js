/**
 * ClubVoice SDK - 用于外部网站集成
 * 允许第三方网站接入 ClubVoice 收听功能
 */
class ClubVoiceSDK {
    constructor(serverUrl = window.location.origin) {
        this.serverUrl = serverUrl.replace(/\/$/, ''); // 移除末尾斜杠
        this.socket = null;
        this.audioContext = null;
        this.isListening = false;
        this.isConnected = false;
        this.playbackGain = null;
        this.nextPlayTime = 0;
        this.playbackLatency = 0.05; // 50ms 播放延迟
        
        // 音频参数
        this.sampleRate = 48000;
        this.channels = 2;
        
        // 统计信息
        this.stats = {
            packetsReceived: 0,
            bytesReceived: 0,
            connectionTime: null
        };

        // 回调函数
        this.onConnected = null;
        this.onDisconnected = null;
        this.onError = null;
        this.onListeningChanged = null;
        this.onAudioReceived = null;
    }

    /**
     * 初始化连接
     */
    async init() {
        try {
            // 动态加载 Socket.IO（如果未加载）
            if (!window.io) {
                await this.loadSocketIO();
            }
            
            // 建立连接
            this.socket = io(this.serverUrl, {
                transports: ['websocket', 'polling'],
                timeout: 10000,
                forceNew: true
            });
            
            // 绑定事件
            this.socket.on('connect', () => {
                console.log('[ClubVoice SDK] 已连接到服务器');
                this.isConnected = true;
                this.stats.connectionTime = new Date();
            });
            
            this.socket.on('connected', (data) => {
                console.log(`[ClubVoice SDK] 客户端ID: ${data.client_id}`);
                if (this.onConnected) {
                    this.onConnected(data);
                }
            });
            
            this.socket.on('disconnect', () => {
                console.log('[ClubVoice SDK] 连接断开');
                this.isConnected = false;
                this.isListening = false;
                if (this.onDisconnected) {
                    this.onDisconnected();
                }
            });
            
            this.socket.on('audio_from_clubdeck', (data) => {
                this.handleIncomingAudio(data);
            });
            
            this.socket.on('connect_error', (error) => {
                console.error('[ClubVoice SDK] 连接错误:', error);
                if (this.onError) {
                    this.onError(error);
                }
            });
            
            // 等待连接建立
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('连接超时'));
                }, 10000);
                
                this.socket.on('connected', () => {
                    clearTimeout(timeout);
                    resolve();
                });

                this.socket.on('connect_error', () => {
                    clearTimeout(timeout);
                    reject(new Error('连接失败'));
                });
            });
        } catch (error) {
            console.error('[ClubVoice SDK] 初始化失败:', error);
            if (this.onError) {
                this.onError(error);
            }
            throw error;
        }
    }

    /**
     * 开始收听 Clubdeck
     */
    async startListening() {
        if (this.isListening) {
            console.warn('[ClubVoice SDK] 已在收听中');
            return true;
        }
        
        if (!this.isConnected) {
            throw new Error('未连接到服务器，请先调用 init()');
        }
        
        try {
            // 初始化音频上下文
            await this.initAudioContext();
            
            this.isListening = true;
            console.log('[ClubVoice SDK] 开始收听');
            
            if (this.onListeningChanged) {
                this.onListeningChanged(true);
            }
            
            return true;
        } catch (error) {
            console.error('[ClubVoice SDK] 启动收听失败:', error);
            if (this.onError) {
                this.onError(error);
            }
            throw error;
        }
    }

    /**
     * 停止收听
     */
    stopListening() {
        if (!this.isListening) {
            return;
        }
        
        this.isListening = false;
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.suspend();
        }
        
        console.log('[ClubVoice SDK] 停止收听');
        
        if (this.onListeningChanged) {
            this.onListeningChanged(false);
        }
    }

    /**
     * 设置音量 (0.0 - 1.0)
     */
    setVolume(volume) {
        if (this.playbackGain && this.audioContext) {
            volume = Math.max(0, Math.min(1, volume));
            this.playbackGain.gain.setValueAtTime(
                volume, 
                this.audioContext.currentTime
            );
        }
    }

    /**
     * 获取连接状态
     */
    getStatus() {
        return {
            connected: this.isConnected,
            listening: this.isListening,
            serverUrl: this.serverUrl,
            stats: { ...this.stats }
        };
    }

    /**
     * 断开连接
     */
    disconnect() {
        this.stopListening();
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
        }
        
        this.isConnected = false;
        console.log('[ClubVoice SDK] 已断开连接');
    }

    // === 内部方法 ===

    async initAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });
        }
        
        // 恢复音频上下文（需要用户手势）
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
        
        // 创建播放增益节点
        if (!this.playbackGain) {
            this.playbackGain = this.audioContext.createGain();
            this.playbackGain.connect(this.audioContext.destination);
            this.playbackGain.gain.setValueAtTime(0.8, this.audioContext.currentTime);
        }
    }

    handleIncomingAudio(data) {
        if (!this.isListening || !this.audioContext) {
            return;
        }
        
        try {
            // 解码音频数据
            const int16Data = this.base64ToInt16Array(data.audio);
            const channels = data.channels || this.channels;
            const { left, right } = this.int16StereoToFloat32(int16Data, channels);
            
            // 播放音频
            this.playAudioStereo(left, right);
            
            // 更新统计
            this.stats.packetsReceived++;
            this.stats.bytesReceived += data.audio.length;
            
            // 触发回调
            if (this.onAudioReceived) {
                this.onAudioReceived({
                    channels,
                    samples: int16Data.length / channels,
                    volume: this.calculateVolume(left)
                });
            }
        } catch (error) {
            console.error('[ClubVoice SDK] 音频处理错误:', error);
        }
    }

    playAudioStereo(leftData, rightData) {
        const buffer = this.audioContext.createBuffer(
            2, 
            leftData.length, 
            this.audioContext.sampleRate
        );
        
        buffer.getChannelData(0).set(leftData);
        buffer.getChannelData(1).set(rightData);

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(this.playbackGain);
        
        // 计算播放时间（避免音频断断续续）
        const currentTime = this.audioContext.currentTime;
        if (this.nextPlayTime < currentTime) {
            this.nextPlayTime = currentTime + this.playbackLatency;
        }
        
        source.start(this.nextPlayTime);
        this.nextPlayTime += buffer.duration;
    }

    // 工具函数
    base64ToInt16Array(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return new Int16Array(bytes.buffer);
    }

    int16StereoToFloat32(int16Array, channels) {
        if (channels === 1) {
            // 单声道转立体声
            const float32Array = new Float32Array(int16Array.length);
            for (let i = 0; i < int16Array.length; i++) {
                float32Array[i] = int16Array[i] / 0x8000;
            }
            return { left: float32Array, right: float32Array };
        } else {
            // 立体声分离
            const length = int16Array.length / 2;
            const left = new Float32Array(length);
            const right = new Float32Array(length);
            for (let i = 0; i < length; i++) {
                left[i] = int16Array[i * 2] / 0x8000;
                right[i] = int16Array[i * 2 + 1] / 0x8000;
            }
            return { left, right };
        }
    }

    calculateVolume(data) {
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
            sum += Math.abs(data[i]);
        }
        return (sum / data.length) * 100;
    }

    async loadSocketIO() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.socket.io/4.7.2/socket.io.min.js';
            script.onload = resolve;
            script.onerror = () => reject(new Error('Socket.IO 加载失败'));
            document.head.appendChild(script);
        });
    }
}

// 导出到全局
window.ClubVoiceSDK = ClubVoiceSDK;

// 如果支持模块系统，也导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ClubVoiceSDK;
}