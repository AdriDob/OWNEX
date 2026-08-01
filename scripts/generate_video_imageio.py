"""Generate video using imageio-ffmpeg.

Simple slideshow video generation using imageio with ffmpeg bundled.
"""

from pathlib import Path
import sys
import numpy as np

VIDEO_DIR = Path("assets/video")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# Images to include
IMAGES = [
    "assets/branding/logos_png/ownex_main_logo_v2.png",
    "assets/branding/banners_png/hero_banner_v2.png",
    "assets/branding/logos_png/alpha_logo_v2.png",
    "assets/branding/logos_png/omega_logo_v2.png",
    "assets/branding/concepts_png/product_overview_v2.png",
    "assets/branding/concepts_png/mission_control_v2.png",
    "assets/branding/concepts_png/architecture_diagram_v2.png",
    "assets/branding/concepts_png/mobile_experience_v2.png",
    "assets/branding/concepts_png/boot_sequence_v2.png",
    "assets/branding/logos_png/ownex_main_logo_v2.png",
]

DURATIONS = [3, 5, 3, 3, 8, 8, 8, 8, 6, 3]  # seconds per image
FPS = 30

def generate_video_with_imageio():
    """Generate video using imageio."""
    try:
        import imageio
        print("✓ imageio imported successfully")
    except ImportError:
        print("❌ imageio not installed. Installing...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio"])
            import imageio
            print("✓ imageio installed successfully")
        except Exception as e:
            print(f"❌ Cannot install imageio: {e}")
            return

    try:
        from PIL import Image
        print("✓ PIL imported successfully")
    except ImportError:
        print("❌ PIL not installed. Installing...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
            from PIL import Image
            print("✓ PIL installed successfully")
        except Exception as e:
            print(f"❌ Cannot install PIL: {e}")
            return

    # Check if images exist
    missing_images = []
    for img_path in IMAGES:
        if not Path(img_path).exists():
            missing_images.append(img_path)

    if missing_images:
        print(f"❌ Missing images: {missing_images}")
        return

    print(f"✓ All {len(IMAGES)} images found")

    try:
        # Read first image to get dimensions
        first_img = Image.open(IMAGES[0])
        width, height = first_img.size
        print(f"✓ Image dimensions: {width}x{height}")

        # Create writer
        output_path = VIDEO_DIR / "ownex_presentation_v2.mp4"
        print(f"🎬 Generating video to: {output_path}")

        # Use imageio's ffmpeg writer
        writer = imageio.get_writer(str(output_path), fps=FPS, codec='libx264', quality=8)

        # Process each image
        for img_path, duration in zip(IMAGES, DURATIONS):
            # Read image
            img = Image.open(img_path)
            img_array = np.array(img)

            # Repeat frames for duration
            frames_count = int(duration * FPS)
            for _ in range(frames_count):
                writer.append_data(img_array)

            print(f"✓ Processed: {img_path} ({duration}s)")

        writer.close()
        print(f"✓ Video generated successfully: {output_path}")

    except Exception as e:
        print(f"❌ Error generating video: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("OWNEX Video Generator using imageio")
    print("=" * 50)
    generate_video_with_imageio()
