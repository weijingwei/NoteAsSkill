"""图标生成脚本

将SVG图标转换为不同尺寸的PNG和ICO文件。
"""

from pathlib import Path
import subprocess

def create_png_from_svg(svg_path: Path, output_dir: Path, sizes: list[int]):
    """使用Inkscape或cairosvg将SVG转换为PNG"""
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import cairosvg
        for size in sizes:
            output_path = output_dir / f"icon_{size}x{size}.png"
            cairosvg.svg2png(url=str(svg_path), write_to=str(output_path),
                           output_width=size, output_height=size)
            print(f"Created: {output_path}")
        return True
    except ImportError:
        print("cairosvg not installed, trying alternative method...")

    # 尝试使用inkscape
    try:
        for size in sizes:
            output_path = output_dir / f"icon_{size}x{size}.png"
            subprocess.run([
                "inkscape", str(svg_path),
                "--export-type=png",
                f"--export-width={size}",
                f"--export-height={size}",
                f"--export-filename={output_path}"
            ], check=True, capture_output=True)
            print(f"Created: {output_path}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Inkscape not found. Please install cairosvg: pip install cairosvg")

    return False

def create_ico_from_png(png_dir: Path, output_path: Path):
    """从PNG文件创建ICO文件"""
    try:
        from PIL import Image

        # 收集所有PNG文件
        png_files = sorted(png_dir.glob("icon_*.png"))
        if not png_files:
            print("No PNG files found")
            return False

        images = [Image.open(f) for f in png_files]

        # 保存为ICO
        images[0].save(output_path, format='ICO', sizes=[(i.width, i.height) for i in images])
        print(f"Created: {output_path}")
        return True
    except ImportError:
        print("PIL not installed. Please install: pip install Pillow")
        return False

def main():
    base_dir = Path(__file__).parent.parent
    svg_path = base_dir / "assets" / "icon.svg"
    png_dir = base_dir / "assets" / "icons"

    if not svg_path.exists():
        print(f"SVG file not found: {svg_path}")
        return

    sizes = [16, 24, 32, 48, 64, 128, 256]

    # 创建PNG
    if create_png_from_svg(svg_path, png_dir, sizes):
        # 创建ICO
        create_ico_from_png(png_dir, base_dir / "assets" / "icon.ico")

if __name__ == "__main__":
    main()