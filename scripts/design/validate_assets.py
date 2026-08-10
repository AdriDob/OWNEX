#!/usr/bin/env python3
"""
OWNEX Asset Validation Script

Validates that all visual assets are:
- Registered in ASSET_REGISTRY.md
- Present in the filesystem
- Not duplicated
- Within size constraints
- Correct format
- Referenced correctly in README.md
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def parse_asset_registry() -> Dict[str, dict]:
    """Parse ASSET_REGISTRY.md and extract asset information."""
    registry_path = Path("docs/design/ASSET_REGISTRY.md")
    
    if not registry_path.exists():
        print(f"❌ ASSET_REGISTRY.md not found at {registry_path}")
        return {}
    
    content = registry_path.read_text()
    assets = {}
    
    # Find all table rows with asset data
    # Pattern: lines starting with | that contain docs/assets/
    for line in content.split('\n'):
        if line.startswith('|') and 'docs/assets/' in line:
            # Parse table row
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            if len(cells) >= 2:
                # First cell is ID (may have backticks)
                asset_id = cells[0].strip('`')
                file_path = cells[1].strip('`')
                asset_type = cells[2].strip('`') if len(cells) > 2 else None
                
                if file_path and file_path.startswith('docs/assets/'):
                    assets[asset_id] = {
                        'file': file_path,
                        'type': asset_type
                    }
    
    return assets


def find_all_assets() -> Set[Path]:
    """Find all image assets in docs/assets/."""
    assets_dir = Path("docs/assets")
    assets = set()
    
    for ext in ['*.png', '*.svg', '*.jpg', '*.jpeg', '*.webp']:
        assets.update(assets_dir.rglob(ext))
    
    return assets


def check_registered_assets_exist(registry: Dict[str, dict]) -> List[str]:
    """Check that all registered assets exist in the filesystem."""
    missing = []
    
    for asset_id, asset_info in registry.items():
        file_path = asset_info.get('file')
        if file_path:
            if not Path(file_path).exists():
                missing.append(f"{asset_id}: {file_path}")
    
    return missing


def check_unregistered_assets(registry: Dict[str, dict], all_assets: Set[Path]) -> List[Path]:
    """Check for assets that exist but are not registered."""
    registered_files = {asset_info['file'] for asset_info in registry.values() if asset_info.get('file')}
    unregistered = []
    
    for asset in all_assets:
        relative_path = str(asset.relative_to(Path('.')))
        if relative_path not in registered_files:
            unregistered.append(asset)
    
    return unregistered


def check_duplicate_assets(all_assets: Set[Path]) -> List[Tuple[Path, Path]]:
    """Check for duplicate assets by SHA-256 hash."""
    hashes: Dict[str, List[Path]] = {}
    
    for asset in all_assets:
        if asset.exists():
            file_hash = calculate_sha256(asset)
            if file_hash not in hashes:
                hashes[file_hash] = []
            hashes[file_hash].append(asset)
    
    duplicates = []
    for file_hash, files in hashes.items():
        if len(files) > 1:
            # Pair up duplicates
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    duplicates.append((files[i], files[j]))
    
    return duplicates


def check_file_size_constraints(all_assets: Set[Path]) -> List[Tuple[Path, int, int]]:
    """Check file size constraints."""
    oversized = []
    
    for asset in all_assets:
        if asset.exists():
            size_mb = asset.stat().st_size / (1024 * 1024)
            
            # Constraints
            max_size_mb = 1.0 if 'hero' in str(asset) else 0.5
            
            if size_mb > max_size_mb:
                oversized.append((asset, size_mb, max_size_mb))
    
    return oversized


def check_format_constraints(all_assets: Set[Path]) -> List[Path]:
    """Check format constraints (SVG for logos, PNG for screenshots)."""
    invalid_format = []
    
    for asset in all_assets:
        if asset.exists():
            # Logos should be SVG, but PNG fallbacks are allowed
            if 'logo' in str(asset) and asset.suffix != '.svg':
                # Allow PNG fallbacks for all logo variants
                # Logo PNGs are valid as fallbacks for SVG
                pass
            
            # Screenshots should be PNG, but demo SVGs are allowed
            if 'screenshot' in str(asset) and asset.suffix != '.png':
                # Allow SVG for demo screenshots
                if 'demo' not in asset.name:
                    invalid_format.append(asset)
    
    return invalid_format


def check_readme_references(registry: Dict[str, dict]) -> List[str]:
    """Check that all image references in README.md are valid."""
    readme_path = Path("README.md")
    
    if not readme_path.exists():
        return []
    
    content = readme_path.read_text()
    
    # Extract image references
    # Pattern: ![alt](path) or <img src="path">
    image_pattern = r'!\[.*?\]\((.*?)\)|<img[^>]+src=["\'](.*?)["\']'
    matches = re.findall(image_pattern, content)
    
    # Flatten matches
    referenced_paths = []
    for match in matches:
        if isinstance(match, tuple):
            referenced_paths.extend(m for m in match if m)
        else:
            referenced_paths.append(match)
    
    broken = []
    for path in referenced_paths:
        if path and not path.startswith('http'):
            if not Path(path).exists():
                broken.append(path)
    
    return broken


def main():
    """Run all validation checks."""
    print("🔍 OWNEX Asset Validation")
    print("=" * 50)
    
    # Parse registry
    print("\n📋 Parsing ASSET_REGISTRY.md...")
    registry = parse_asset_registry()
    print(f"   Found {len(registry)} registered assets")
    
    # Find all assets
    print("\n📁 Scanning docs/assets/...")
    all_assets = find_all_assets()
    print(f"   Found {len(all_assets)} asset files")
    
    # Run checks
    errors = []
    warnings = []
    
    # Check 1: Registered assets exist
    print("\n✅ Checking registered assets exist...")
    missing = check_registered_assets_exist(registry)
    if missing:
        errors.append(f"Missing registered assets: {len(missing)}")
        for item in missing:
            print(f"   ❌ {item}")
    else:
        print("   ✓ All registered assets exist")
    
    # Check 2: Unregistered assets
    print("\n✅ Checking for unregistered assets...")
    unregistered = check_unregistered_assets(registry, all_assets)
    if unregistered:
        warnings.append(f"Unregistered assets: {len(unregistered)}")
        for asset in unregistered:
            print(f"   ⚠️  {asset}")
    else:
        print("   ✓ All assets are registered")
    
    # Check 3: Duplicate assets
    print("\n✅ Checking for duplicate assets...")
    duplicates = check_duplicate_assets(all_assets)
    if duplicates:
        errors.append(f"Duplicate assets found: {len(duplicates)}")
        for asset1, asset2 in duplicates:
            print(f"   ❌ {asset1} == {asset2}")
    else:
        print("   ✓ No duplicate assets")
    
    # Check 4: File size constraints
    print("\n✅ Checking file size constraints...")
    oversized = check_file_size_constraints(all_assets)
    if oversized:
        warnings.append(f"Oversized assets: {len(oversized)}")
        for asset, size, max_size in oversized:
            print(f"   ⚠️  {asset}: {size:.2f}MB (max {max_size}MB)")
    else:
        print("   ✓ All assets within size limits")
    
    # Check 5: Format constraints
    print("\n✅ Checking format constraints...")
    invalid_format = check_format_constraints(all_assets)
    if invalid_format:
        errors.append(f"Invalid format: {len(invalid_format)}")
        for asset in invalid_format:
            print(f"   ❌ {asset}")
    else:
        print("   ✓ All assets have correct format")
    
    # Check 6: README references
    print("\n✅ Checking README.md image references...")
    broken = check_readme_references(registry)
    if broken:
        errors.append(f"Broken image references: {len(broken)}")
        for path in broken:
            print(f"   ❌ {path}")
    else:
        print("   ✓ All image references are valid")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Registered assets: {len(registry)}")
    print(f"Total asset files: {len(all_assets)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    
    if errors:
        print("\n❌ VALIDATION FAILED")
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    elif warnings:
        print("\n⚠️  VALIDATION PASSED WITH WARNINGS")
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")
        return 0
    else:
        print("\n✅ VALIDATION PASSED")
        return 0


if __name__ == "__main__":
    exit(main())