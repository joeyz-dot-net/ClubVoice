"""
调试配置加载
"""
from src.config.settings import config

print("=" * 70)
print("当前配置信息:")
print("=" * 70)

print(f"\nclubdeck_input_device_id = {config.audio.clubdeck_input_device_id}")
print(f"mpv_input_device_id = {config.audio.mpv_input_device_id}")
print(f"browser_output_device_id = {config.audio.browser_output_device_id}")

print(f"\nmix_mode = {config.audio.mix_mode}")
print(f"duplex_mode = {config.audio.duplex_mode}")

print(f"\n向后兼容字段:")
print(f"input_device_id_2 = {config.audio.input_device_id_2}")
print(f"input_device_id = {config.audio.input_device_id}")
print(f"output_device_id = {config.audio.output_device_id}")

print("=" * 70)
