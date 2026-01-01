#!/usr/bin/env python
"""
生成 ClubVoice PWA 图标
需要安装: pip install pillow
"""
import sys
import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("错误: 需要安装 Pillow 库")
    print("运行: pip install pillow")
    sys.exit(1)


def create_icon(size, output_path):
    """创建 ClubVoice 图标"""
    # 创建背景
    img = Image.new('RGB', (size, size), color='#16213e')
    draw = ImageDraw.Draw(img)
    
    # 计算尺寸
    center_x = size // 2
    center_y = size // 2
    
    # 麦克风主体尺寸
    mic_width = size // 4
    mic_height = size // 3
    mic_top = center_y - mic_height // 2
    mic_bottom = mic_top + mic_height
    mic_left = center_x - mic_width // 2
    mic_right = center_x + mic_width // 2
    
    # 绘制麦克风主体（圆角矩形）
    draw.rounded_rectangle(
        [mic_left, mic_top, mic_right, mic_bottom],
        radius=mic_width // 2,
        fill='#2ecc71',
        outline='#27ae60',
        width=max(2, size // 50)
    )
    
    # 绘制麦克风支架
    stand_top = mic_bottom + size // 20
    stand_bottom = stand_top + size // 8
    stand_width = max(3, size // 30)
    
    # 垂直支架
    draw.line(
        [center_x, mic_bottom, center_x, stand_top],
        fill='#2ecc71',
        width=stand_width
    )
    
    # 底座
    base_width = mic_width
    draw.arc(
        [center_x - base_width // 2, stand_top - size // 20, 
         center_x + base_width // 2, stand_bottom],
        start=0,
        end=180,
        fill='#2ecc71',
        width=stand_width
    )
    
    # 添加装饰线（网格效果）
    grid_lines = 3
    line_spacing = mic_height // (grid_lines + 1)
    for i in range(1, grid_lines + 1):
        y = mic_top + line_spacing * i
        draw.line(
            [mic_left + mic_width // 4, y, mic_right - mic_width // 4, y],
            fill='#1e8449',
            width=max(1, size // 100)
        )
    
    # 保存图标
    img.save(output_path, 'PNG', optimize=True)
    print(f'✓ 生成图标: {output_path} ({size}x{size})')


def main():
    """生成所有尺寸的图标"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    static_dir = project_root / 'static'
    
    # 确保 static 目录存在
    static_dir.mkdir(exist_ok=True)
    
    # 需要生成的图标尺寸
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    print('开始生成 ClubVoice PWA 图标...\n')
    
    for size in sizes:
        output_path = static_dir / f'icon-{size}.png'
        try:
            create_icon(size, output_path)
        except Exception as e:
            print(f'✗ 生成 {size}x{size} 图标失败: {e}')
    
    print('\n图标生成完成！')
    print(f'输出目录: {static_dir}')
    
    # 额外生成 favicon
    try:
        favicon_path = static_dir / 'favicon.ico'
        img_32 = Image.new('RGB', (32, 32), color='#16213e')
        draw = ImageDraw.Draw(img_32)
        
        # 简化的麦克风图标
        draw.rounded_rectangle(
            [8, 6, 24, 20],
            radius=4,
            fill='#2ecc71'
        )
        draw.line([16, 20, 16, 26], fill='#2ecc71', width=2)
        draw.arc([10, 22, 22, 30], start=0, end=180, fill='#2ecc71', width=2)
        
        img_32.save(favicon_path, format='ICO', sizes=[(32, 32)])
        print(f'✓ 生成 favicon: {favicon_path}')
    except Exception as e:
        print(f'✗ 生成 favicon 失败: {e}')


if __name__ == '__main__':
    main()
