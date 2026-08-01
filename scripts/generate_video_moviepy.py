"""Generate video using MoviePy.

Attempts to create video from branding images using Python MoviePy library.
"""

from pathlib import Path
import sys

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

def generate_video_with_moviepy():
    """Generate video using MoviePy."""
    try:
        from moviepy import ImageSequenceClip, CompositeVideoClip, TextClip, ColorClip
        print("✓ MoviePy imported successfully")
    except ImportError:
        print("❌ MoviePy not installed. Installing...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "moviepy"])
            from moviepy import ImageSequenceClip, CompositeVideoClip, TextClip, ColorClip
            print("✓ MoviePy installed successfully")
        except Exception as e:
            print(f"❌ Cannot install MoviePy: {e}")
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
        # Create image sequence with durations
        clips = []
        for img_path, duration in zip(IMAGES, DURATIONS):
            from moviepy.editor import ImageClip
            clip = ImageClip(img_path, duration=duration)
            clips.append(clip)

        # Concatenate clips
        final_clip = ImageSequenceClip(IMAGES, durations=DURATIONS)

        # Set FPS
        final_clip = final_clip.set_fps(30)

        # Write video
        output_path = VIDEO_DIR / "ownex_presentation_v2.mp4"
        print(f"🎬 Generating video to: {output_path}")
        final_clip.write_videofile(str(output_path), codec='libx264', audio_codec='aac')

        print(f"✓ Video generated successfully: {output_path}")

    except Exception as e:
        print(f"❌ Error generating video: {e}")
        print("This may require additional dependencies (ffmpeg, imageio-ffmpeg)")

if __name__ == "__main__":
    print("OWNEX Video Generator using MoviePy")
    print("=" * 50)
    generate_video_with_moviepy()
