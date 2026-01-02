"""
测试音频闪避功能 - MPV 版本
"""
import numpy as np
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.voice_detector import VoiceActivityDetector, VoiceDetectionConfig
from src.audio.mpv_controller import MPVController, MPVConfig


def test_voice_detection():
    """测试语音活动检测"""
    print("\n" + "="*60)
    print("测试: 语音活动检测 (VAD)")
    print("="*60)
    
    detector = VoiceActivityDetector(
        sample_rate=48000,
        config=VoiceDetectionConfig(
            threshold=150.0,
            min_duration=0.1,
            release_time=0.5
        )
    )
    
    print("\n1. 测试静音检测...")
    silent = np.zeros(512, dtype=np.int16)
    result = detector.detect(silent)
    print(f"  静音音频 → 检测结果: {result} (期望: False)")
    assert result == False, "静音应该不被检测为语音"
    
    print("\n2. 测试噪声检测...")
    noise = np.random.randint(-100, 100, 512, dtype=np.int16)
    result = detector.detect(noise)
    print(f"  噪声音频 (低于阈值) → 检测结果: {result} (期望: False)")
    assert result == False, "低于阈值的噪声不应被检测为语音"
    
    print("\n3. 测试语音检测...")
    voice = np.random.randint(-5000, 5000, 512, dtype=np.int16)
    
    # 需要连续检测多帧才能触发（min_duration）
    for i in range(10):
        result = detector.detect(voice)
        if i < 3:
            print(f"  帧 {i+1}: 检测中... {result}")
        elif i == 3:
            print(f"  帧 {i+1}: 语音确认! {result} (期望: True)")
            assert result == True, "持续的语音应该被检测到"
    
    print("\n4. 测试释放时间...")
    for i in range(30):
        result = detector.detect(silent)
        if i < 10:
            assert result == True, "释放时间内应保持检测状态"
        elif i == 25:
            print(f"  帧 {i+1}: 语音结束 {result} (期望: False)")
            assert result == False, "释放时间后应停止检测"
    
    print("\n✅ 语音检测测试通过")


def test_mpv_controller():
    """测试 MPV 控制器"""
    print("\n" + "="*60)
    print("测试: MPV 音量控制")
    print("="*60)
    
    config = MPVConfig(
        enabled=True,
        pipe_path=r'\\.\pipe\mpv-pipe',
        normal_volume=100,
        ducking_volume=15,
        transition_time=0.1
    )
    
    controller = MPVController(config)
    
    if not controller.is_enabled():
        print("\n⚠ MPV 未运行，跳过音量控制测试")
        print("  提示: 请启动 MPV 并添加参数:")
        print("  mpv --input-ipc-server=\\\\.\\pipe\\mpv-pipe your-music.mp3")
        return False
    
    print("\n1. 测试设置音量...")
    result = controller.set_volume(50)
    if result:
        print(f"✓ 音量设置为 50%")
    time.sleep(0.5)
    
    print("\n2. 测试音频闪避 (降低音量)...")
    controller.set_ducking(True)
    print(f"  启用闪避，等待过渡...")
    time.sleep(0.5)
    
    current = controller.get_current_volume()
    print(f"  当前音量: {current}% (目标: {controller.ducking_volume}%)")
    
    print("\n3. 测试恢复音量...")
    controller.set_ducking(False)
    time.sleep(0.5)
    
    current = controller.get_current_volume()
    print(f"  当前音量: {current}% (目标: {controller.normal_volume}%)")
    
    controller.stop()
    print("\n✅ MPV 控制器测试完成")
    return True


def test_integration_with_mpv():
    """集成测试：语音检测 + MPV 控制"""
    print("\n" + "="*60)
    print("测试: 集成测试（语音检测 + MPV 控制）")
    print("="*60)
    
    # 初始化
    detector = VoiceActivityDetector(
        sample_rate=48000,
        config=VoiceDetectionConfig(threshold=150.0)
    )
    
    mpv_config = MPVConfig(
        enabled=True,
        pipe_path=r'\\.\pipe\mpv-pipe',
        normal_volume=100,
        ducking_volume=15,
        transition_time=0.1
    )
    mpv = MPVController(mpv_config)
    
    if not mpv.is_enabled():
        print("⚠ MPV 未运行，跳过集成测试")
        return
    
    print("\n场景：播放音乐 → 有人说话 → 音乐降低 → 说话结束 → 音乐恢复")
    print("-" * 60)
    
    # 场景 1: 只有音乐
    print("\n1. 只有音乐播放（无语音）...")
    clubdeck_silent = np.zeros(512, dtype=np.int16)
    
    for frame in range(3):
        has_voice = detector.detect(clubdeck_silent)
        mpv.set_ducking(has_voice)
        vol = mpv.get_current_volume()
        print(f"  帧 {frame+1}: 语音={has_voice}, MPV 音量={vol}%")
        time.sleep(0.1)
    
    # 场景 2: 有人说话
    print("\n2. Clubdeck 有人说话...")
    clubdeck_voice = np.random.randint(-5000, 5000, 512, dtype=np.int16)
    
    for frame in range(10):
        has_voice = detector.detect(clubdeck_voice)
        mpv.set_ducking(has_voice)
        vol = mpv.get_current_volume()
        if frame % 2 == 0:
            print(f"  帧 {frame+1}: 语音={has_voice}, MPV 音量={vol}%")
        time.sleep(0.1)
    
    # 场景 3: 说话结束
    print("\n3. 说话结束，音乐恢复...")
    for frame in range(15):
        has_voice = detector.detect(clubdeck_silent)
        mpv.set_ducking(has_voice)
        vol = mpv.get_current_volume()
        if frame % 3 == 0:
            print(f"  帧 {frame+1}: 语音={has_voice}, MPV 音量={vol}%")
        time.sleep(0.1)
    
    mpv.stop()
    print("\n✅ 集成测试完成")


def main():
    """主测试函数"""
    print("="*60)
    print("🎵 MPV Audio Ducking 测试")
    print("="*60)
    print("\n⚠ 测试要求:")
    print("  1. MPV 正在运行并播放音乐")
    print("  2. MPV 启用了 IPC:")
    print("     mpv --input-ipc-server=\\\\.\\pipe\\mpv-pipe your-music.mp3")
    print("\n💡 如果 MPV 未运行，语音检测测试仍会执行")
    
    input("\n按 Enter 开始测试...")
    
    try:
        # 测试 1: 语音检测（不需要 MPV）
        test_voice_detection()
        
        # 测试 2: MPV 控制器
        mpv_available = test_mpv_controller()
        
        # 测试 3: 集成测试（需要 MPV）
        if mpv_available:
            test_integration_with_mpv()
        
        print("\n" + "="*60)
        print("🎉 所有测试完成！")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
