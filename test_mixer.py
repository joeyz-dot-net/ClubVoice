"""
测试混音功能
"""
from src.config.settings import config
from src.audio.device_manager import DeviceManager

def main():
    print("="*60)
    print("测试混音配置")
    print("="*60)
    
    print(f"\n混音模式: {'启用' if config.audio.mix_mode else '禁用'}")
    print(f"输入设备1 ID: {config.audio.input_device_id}")
    print(f"输入设备2 ID: {config.audio.input_device_id_2}")
    
    # 获取设备信息
    device_manager = DeviceManager()
    
    device1 = device_manager.get_device_info(config.audio.input_device_id)
    device2 = device_manager.get_device_info(config.audio.input_device_id_2)
    
    if device1:
        print(f"\n设备1信息:")
        print(f"  名称: {device1['name']}")
        print(f"  采样率: {device1['sample_rate']} Hz")
        print(f"  输入通道: {device1['input_channels']} ch")
        print(f"  输出通道: {device1['output_channels']} ch")
    
    if device2:
        print(f"\n设备2信息:")
        print(f"  名称: {device2['name']}")
        print(f"  采样率: {device2['sample_rate']} Hz")
        print(f"  输入通道: {device2['input_channels']} ch")
        print(f"  输出通道: {device2['output_channels']} ch")
    
    print("\n" + "="*60)
    print("配置测试完成！")
    print("="*60)

if __name__ == '__main__':
    main()
