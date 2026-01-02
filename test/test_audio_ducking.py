"""
测试音频闪避功能
"""
import numpy as np
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.voice_detector import VoiceActivityDetector, VoiceDetectionConfig
from src.audio.audio_ducker import AudioDucker


def test_voice_detection():
    """测试语音检测"""
    print("\n" + "="*60)
    print("测试 1: 语音活动检测")
    print("="*60)
    
    detector = VoiceActivityDetector(
        sample_rate=48000,
        config=VoiceDetectionConfig(
            threshold=150.0,
            min_duration=0.1,
            release_time=0.5
        )
    )
    
    # 测试静音
    print("\n1. 测试静音音频...")
    silent = np.zeros(512, dtype=np.int16)
    for i in range(5):
        result = detector.detect(silent)
        assert not result, f"第{i+1}帧: 静音不应该被检测为语音"
    print("✓ 静音检测正确")
    
    # 测试低音量
    print("\n2. 测试低音量音频...")
    low_vol = np.random.randint(-100, 100, 512, dtype=np.int16)
    for i in range(5):
        result = detector.detect(low_vol)
        assert not result, f"第{i+1}帧: 低音量不应该被检测为语音"
    print("✓ 低音量检测正确")
    
    # 测试语音（高幅度）
    print("\n3. 测试语音音频...")
    voice = np.random.randint(-5000, 5000, 512, dtype=np.int16)
    voice_detected = False
    for i in range(10):
        result = detector.detect(voice)
        if result:
            voice_detected = True
            print(f"✓ 第{i+1}帧: 检测到语音")
            break
    assert voice_detected, "高幅度音频应该被检测为语音"
    
    # 测试释放
    print("\n4. 测试语音停止后的释放...")
    for i in range(30):
        result = detector.detect(silent)
        if not result:
            print(f"✓ 第{i+1}帧: 语音已释放")
            break
    
    print("\n✅ 语音检测测试通过")


def test_audio_ducking():
    """测试音频闪避"""
    print("\n" + "="*60)
    print("测试 2: 音频闪避控制")
    print("="*60)
    
    ducker = AudioDucker(
        sample_rate=48000,
        normal_gain=1.0,
        ducked_gain=0.15,
        transition_time=0.1
    )
    
    # 测试初始状态
    print("\n1. 测试初始状态...")
    audio = np.ones(512, dtype=np.int16) * 10000
    result = ducker.process(audio)
    initial_volume = np.mean(np.abs(result))
    print(f"初始音量: {initial_volume:.1f}")
    assert initial_volume > 9000, "初始状态应该无增益变化"
    print("✓ 初始状态正确")
    
    # 测试闪避开启
    print("\n2. 测试启用闪避...")
    ducker.set_ducking(True)
    
    # 多次处理以完成过渡
    for i in range(20):
        result = ducker.process(audio)
        current_gain = ducker.get_current_gain()
        if i % 5 == 0:
            print(f"  第{i+1}帧: 增益 = {current_gain:.2f} ({int(current_gain*100)}%)")
    
    final_gain = ducker.get_current_gain()
    print(f"最终增益: {final_gain:.2f}")
    assert final_gain < 0.2, "启用闪避后增益应该降到 0.15"
    
    final_volume = np.mean(np.abs(result))
    print(f"最终音量: {final_volume:.1f}")
    assert final_volume < initial_volume * 0.2, "音量应该降低到 15%"
    print("✓ 闪避生效")
    
    # 测试闪避关闭
    print("\n3. 测试关闭闪避...")
    ducker.set_ducking(False)
    
    for i in range(20):
        result = ducker.process(audio)
        current_gain = ducker.get_current_gain()
        if i % 5 == 0:
            print(f"  第{i+1}帧: 增益 = {current_gain:.2f} ({int(current_gain*100)}%)")
    
    recovered_gain = ducker.get_current_gain()
    print(f"恢复增益: {recovered_gain:.2f}")
    assert recovered_gain > 0.95, "关闭闪避后应该恢复到 100%"
    print("✓ 音量恢复正常")
    
    print("\n✅ 音频闪避测试通过")


def test_integration():
    """集成测试：模拟实际使用场景"""
    print("\n" + "="*60)
    print("测试 3: 集成测试（模拟实际场景）")
    print("="*60)
    
    # 初始化检测器和闪避器
    detector = VoiceActivityDetector(
        sample_rate=48000,
        config=VoiceDetectionConfig(threshold=150.0)
    )
    
    ducker = AudioDucker(
        sample_rate=48000,
        normal_gain=1.0,
        ducked_gain=0.15,
        transition_time=0.1
    )
    
    # 模拟音频流
    print("\n场景：播放音乐 → 有人说话 → 音乐降低 → 说话结束 → 音乐恢复")
    print("-" * 60)
    
    # 场景 1: 只有音乐（静音的 Clubdeck）
    print("\n1. 只有音乐播放（无语音）...")
    music = np.ones(512, dtype=np.int16) * 10000
    clubdeck_silent = np.zeros(512, dtype=np.int16)
    
    for frame in range(5):
        has_voice = detector.detect(clubdeck_silent)
        ducker.set_ducking(has_voice)
        ducked_music = ducker.process(music)
        volume = np.mean(np.abs(ducked_music))
        print(f"  帧 {frame+1}: 语音={has_voice}, 音乐音量={volume:.0f} ({ducker.get_current_gain_percent()}%)")
    
    print("✓ 音乐正常播放")
    
    # 场景 2: 有人说话
    print("\n2. Clubdeck 有人说话...")
    clubdeck_voice = np.random.randint(-5000, 5000, 512, dtype=np.int16)
    
    for frame in range(25):  # 增加到 25 帧确保完全过渡
        has_voice = detector.detect(clubdeck_voice)
        ducker.set_ducking(has_voice)
        ducked_music = ducker.process(music)
        volume = np.mean(np.abs(ducked_music))
        if frame % 3 == 0:
            print(f"  帧 {frame+1}: 语音={has_voice}, 音乐音量={volume:.0f} ({ducker.get_current_gain_percent()}%)")
    
    assert ducker.get_current_gain() < 0.2, f"音乐应该降低到 15%，当前: {ducker.get_current_gain():.2f}"
    print("✓ 音乐音量已降低")
    
    # 场景 3: 说话结束
    print("\n3. 说话结束，音乐恢复...")
    for frame in range(60):  # 需要更多帧来完成释放和恢复
        has_voice = detector.detect(clubdeck_silent)
        ducker.set_ducking(has_voice)
        ducked_music = ducker.process(music)
        volume = np.mean(np.abs(ducked_music))
        if frame % 5 == 0:
            print(f"  帧 {frame+1}: 语音={has_voice}, 音乐音量={volume:.0f} ({ducker.get_current_gain_percent()}%)")
        
        # 检查是否已经完全恢复
        if not has_voice and ducker.get_current_gain() > 0.95:
            print(f"✓ 第{frame+1}帧: 语音已停止，音量已恢复")
            break
    else:
        # 如果循环结束还没达到条件，打印当前状态
        if ducker.get_current_gain() <= 0.95:
            print(f"  最终状态: 语音={has_voice}, 增益={ducker.get_current_gain():.2f}")
    
    assert ducker.get_current_gain() > 0.95, f"音乐应该恢复到 100%，当前: {ducker.get_current_gain():.2f}"
    print("✓ 音乐音量已恢复")
    
    print("\n✅ 集成测试通过")


if __name__ == '__main__':
    try:
        test_voice_detection()
        test_audio_ducking()
        test_integration()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！Audio Ducking 功能正常工作")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
