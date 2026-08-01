"""Generate simple presentation video using FFmpeg.

Creates a slideshow video from existing branding images using FFmpeg.
No GPU required - uses existing PNG images with transitions and audio.

Requirements:
- FFmpeg (lightweight, works on CPU)
- Existing branding images
"""

from pathlib import Path
import subprocess
import json

VIDEO_DIR = Path("assets/video")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# Images to include in slideshow (in order)
IMAGES = [
    "assets/branding/professional/ownex_main_logo.png",
    "assets/branding/professional/cinematic_hero_banner.png",
    "assets/branding/professional/alpha_logo.png",
    "assets/branding/professional/omega_logo.png",
    "assets/branding/professional/architecture_diagram.png",
    "assets/branding/professional/mission_control_screenshot.png",
    "assets/branding/professional/merlin_assistant_concept.png",
    "assets/branding/professional/mobile_omega_concept.png",
    "assets/branding/professional/boot_animation_concept.png",
]

# Duration per image (seconds)
DURATION_PER_IMAGE = 4

# Transition duration (seconds)
TRANSITION_DURATION = 1

# Output settings
OUTPUT_FILE = VIDEO_DIR / "ownex_presentation.mp4"
RESOLUTION = "1920x1080"
FPS = 30

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def generate_slideshow():
    """Generate slideshow video using FFmpeg."""
    if not check_ffmpeg():
        print("❌ FFmpeg not installed. Install with:")
        print("   Ubuntu/Debian: sudo apt install ffmpeg")
        print("   macOS: brew install ffmpeg")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        return

    print("✓ FFmpeg detected")

    # Check if images exist
    missing_images = []
    for img_path in IMAGES:
        if not Path(img_path).exists():
            missing_images.append(img_path)

    if missing_images:
        print(f"❌ Missing images: {missing_images}")
        return

    print(f"✓ All {len(IMAGES)} images found")

    # Create FFmpeg command for slideshow
    # Using concat demuxer for sequential images
    concat_file = VIDEO_DIR / "concat.txt"
    with open(concat_file, "w") as f:
        for img_path in IMAGES:
            f.write(f"file '{Path(img_path).absolute()}'\n")
            f.write(f"duration {DURATION_PER_IMAGE}\n")

    # FFmpeg command
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", f"scale={RESOLUTION}:force_original_aspect_ratio,pad={RESOLUTION}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(OUTPUT_FILE)
    ]

    print(f"🎬 Generating slideshow video...")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"   Resolution: {RESOLUTION}")
    print(f"   FPS: {FPS}")
    print(f"   Duration: {len(IMAGES) * DURATION_PER_IMAGE} seconds")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Video generated successfully: {OUTPUT_FILE}")
        else:
            print(f"❌ FFmpeg error: {result.stderr}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Clean up
    if concat_file.exists():
        concat_file.unlink()

def generate_with_transitions():
    """Generate slideshow with fade transitions using FFmpeg."""
    if not check_ffmpeg():
        print("❌ FFmpeg not installed")
        return

    print("✓ FFmpeg detected")

    # Check if images exist
    missing_images = []
    for img_path in IMAGES:
        if not Path(img_path).exists():
            missing_images.append(img_path)

    if missing_images:
        print(f"❌ Missing images: {missing_images}")
        return

    print(f"✓ All {len(IMAGES)} images found")

    # Create filter_complex for slideshow with fades
    filter_parts = []
    inputs = []

    for i, img_path in enumerate(IMAGES):
        input_num = i + 1
        inputs.extend(["-i", str(img_path)])

        if i == 0:
            # First image
            filter_parts.append(f"[{input_num}:v]scale={RESOLUTION}:force_original_aspect_ratio,pad={RESOLUTION}:(ow-iw)/2:(oh-ih)/2[v{input_num}];")
            filter_parts.append(f"[v{input_num}]fade=t=in:st=0:d=1:alpha=1[v{input_num}f]")
        else:
            # Subsequent images with fade in
            filter_parts.append(f"[{input_num}:v]scale={RESOLUTION}:force_original_aspect_ratio,pad={RESOLUTION}:(ow-iw)/2:(oh-ih)/2[v{input_num}];")
            filter_parts.append(f"[v{input_num}]fade=t=in:st=0:d=1:alpha=1[v{input_num}f]")

    # Concatenate with fade transitions
    if len(IMAGES) > 1:
        filter_complex = ""
        current_out = "v1f"
        for i in range(1, len(IMAGES)):
            next_out = f"v{i+1}f"
            filter_complex += f"[{current_out}][{next_out}]xfade=transition=duration=1:offset=0:shape=clip[v{current_out}t{next_out}];"
            current_out = f"v{current_out}t{next_out}"
        filter_complex += f"[{current_out}]"
        filter_parts.append(filter_complex)
    else:
        filter_parts.append("[v1f]")

    # FFmpeg command with filter_complex
    cmd = [
        "ffmpeg",
    ] + inputs + [
        "-filter_complex", "".join(filter_parts),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(OUTPUT_FILE)
    ]

    print(f"🎬 Generating slideshow with transitions...")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"   Resolution: {RESOLUTION}")
    print(f"   FPS: {FPS}")
    print(f"   Duration: ~{len(IMAGES) * DURATION_PER_IMAGE} seconds")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Video generated successfully: {OUTPUT_FILE}")
        else:
            print(f"❌ FFmpeg error: {result.stderr}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("OWNEX Presentation Video Generator")
    print("=" * 50)
    print("\nOption 1: Simple slideshow (no transitions)")
    print("Option 2: Slideshow with fade transitions\n")

    print("Generating simple slideshow...")
    generate_slideshow()

    print("\n" + "=" * 50)
    print("\nFor better results, consider:")
    print("1. Use video editing software (CapCut, DaVinci Resolve, etc.)")
    print("2. Use Canva to create slideshow with effects")
    print("3. Use AI video tools (Runway ML, Pika Labs, etc.)")
    print("4. Hire a professional editor")
