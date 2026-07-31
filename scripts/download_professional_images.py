"""Download professional corporate images from Unsplash for README.

Downloads high-quality professional images for:
- Hero banner
- Work cycle icons
- Background images
"""

import requests
from pathlib import Path

UNSPLASH_IMAGES = {
    "hero_banner": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop",  # Professional data center
    "dashboard": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2070&auto=format&fit=crop",  # Analytics dashboard
    "technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=2070&auto=format&fit=crop",  # Technology abstract
    "code": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?q=80&w=2070&auto=format&fit=crop",  # Code development
    "security": "https://images.unsplash.com/photo-1563986768609-322da13575f3?q=80&w=2070&auto=format&fit=crop",  # Security/lock
    "finance": "https://images.unsplash.com/photo-1554224155-6726b3ff858f?q=80&w=2070&auto=format&fit=crop",  # Finance/charts
}

OUTPUT_DIR = Path("assets/branding/professional")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_image(url: str, filename: str) -> Path:
    """Download image from URL."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    output_path = OUTPUT_DIR / filename
    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"Downloaded: {filename}")
    return output_path


if __name__ == "__main__":
    for name, url in UNSPLASH_IMAGES.items():
        filename = f"{name}.jpg"
        download_image(url, filename)

    print(f"\nAll images downloaded to: {OUTPUT_DIR}")
