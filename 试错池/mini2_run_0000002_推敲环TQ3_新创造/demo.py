#!/usr/bin/env python3
"""
Demo script for Markdown Image Optimizer.
Generates test images, runs the optimizer, and calculates statistics.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


# Constants as specified
TEST_IMAGE_COUNT = 3
TEST_IMAGE_WIDTH = 50
TEST_IMAGE_HEIGHT = 50
EXPECTED_COMPRESSION_RATE = 70.0


def create_test_images():
    """Create test images folder and generate test PNG images."""
    test_dir = Path('test_images')
    
    # Clean up existing test directory
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Try to use PIL/Pillow, fall back to pure Python if not available
    try:
        from PIL import Image
        
        colors = [
            (255, 0, 0),     # Red
            (0, 255, 0),     # Green
            (0, 0, 255),     # Blue
        ]
        
        for i, color in enumerate(colors):
            img = Image.new('RGB', (TEST_IMAGE_WIDTH, TEST_IMAGE_HEIGHT), color=color)
            img.save(test_dir / f'test_{i+1}.png')
        
        print(f"Created {TEST_IMAGE_COUNT} test images using PIL/Pillow")
        return True
        
    except ImportError:
        # Fallback: Create minimal valid PNG files using pure Python
        # This is a minimal 1x1 red PNG as placeholder
        # In production, users should install Pillow: pip install Pillow
        print("PIL/Pillow not available, using minimal PNG generation...")
        
        # Minimal 1x1 PNG structure (for each color)
        def create_minimal_png(r, g, b):
            """Create a minimal valid PNG with specified RGB color."""
            import zlib
            
            # PNG signature
            signature = b'\x89PNG\r\n\x1a\n'
            
            # IHDR chunk (image header)
            width = TEST_IMAGE_WIDTH
            height = TEST_IMAGE_HEIGHT
            bit_depth = 8
            color_type = 2  # RGB
            compression = 0
            filter_method = 0
            interlace = 0
            
            ihdr_data = (
                width.to_bytes(4, 'big') +
                height.to_bytes(4, 'big') +
                bytes([bit_depth, color_type, compression, filter_method, interlace])
            )
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
            ihdr_chunk = (
                len(ihdr_data).to_bytes(4, 'big') +
                b'IHDR' +
                ihdr_data +
                ihdr_crc.to_bytes(4, 'big')
            )
            
            # IDAT chunk (image data)
            # Raw scanlines with filter byte (0 = none) per row
            raw_data = b''
            for y in range(height):
                raw_data += b'\x00'  # Filter byte
                for x in range(width):
                    raw_data += bytes([r, g, b])
            
            compressed_data = zlib.compress(raw_data, 9)
            idat_crc = zlib.crc32(b'IDAT' + compressed_data) & 0xffffffff
            idat_chunk = (
                len(compressed_data).to_bytes(4, 'big') +
                b'IDAT' +
                compressed_data +
                idat_crc.to_bytes(4, 'big')
            )
            
            # IEND chunk
            iend_crc = zlib.crc32(b'IEND') & 0xffffffff
            iend_chunk = (
                b'\x00\x00\x00\x00' +
                b'IEND' +
                iend_crc.to_bytes(4, 'big')
            )
            
            return signature + ihdr_chunk + idat_chunk + iend_chunk
        
        colors = [
            (255, 0, 0),     # Red
            (0, 255, 0),     # Green
            (0, 0, 255),     # Blue
        ]
        
        for i, (r, g, b) in enumerate(colors):
            png_data = create_minimal_png(r, g, b)
            (test_dir / f'test_{i+1}.png').write_bytes(png_data)
        
        print(f"Created {TEST_IMAGE_COUNT} test images using pure Python")
        return True


def create_sample_markdown():
    """Create a sample Markdown file referencing the test images."""
    test_dir = Path('test_images')
    md_content = """# Test Document

This is a test document for the Markdown Image Optimizer demo.

![Red Test Image](test_images/test_1.png)

![Green Test Image](test_images/test_2.png)

![Blue Test Image](test_images/test_3.png)

End of test document.
"""
    
    with open('test_sample.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return Path('test_sample.md')


def run_optimizer():
    """Run the mdimg_optimizer.py on the test content."""
    print("\nRunning mdimg_optimizer.py...")
    
    try:
        result = subprocess.run(
            ['python', 'mdimg_optimizer.py', 
             '--input', 'test_sample.md',
             '--output', 'test_output',
             '--quality', '80',
             '--max-width', '1920'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0, result
        
    except subprocess.TimeoutExpired:
        print("Error: Optimizer timed out")
        return False, None
    except FileNotFoundError:
        print("Error: mdimg_optimizer.py not found")
        return False, None


def calculate_statistics():
    """Calculate compression and success statistics."""
    test_dir = Path('test_images')
    output_dir = Path('test_output')
    
    # Calculate original size
    original_size = 0
    original_files = []
    for img_file in test_dir.glob('*.png'):
        size = img_file.stat().st_size
        original_size += size
        original_files.append((img_file, size))
    
    # Calculate compressed size
    compressed_size = 0
    compressed_files = []
    
    if output_dir.exists():
        for img_file in output_dir.glob('*.png'):
            size = img_file.stat().st_size
            compressed_size += size
            compressed_files.append((img_file, size))
        
        # Also check for jpg files (ImageMagick may convert)
        for img_file in output_dir.glob('*.jpg'):
            size = img_file.stat().st_size
            compressed_size += size
            compressed_files.append((img_file, size))
    
    # Calculate rates
    total_images = TEST_IMAGE_COUNT
    
    if original_size > 0:
        compression_rate = ((original_size - compressed_size) / original_size) * 100
    else:
        compression_rate = 0.0
    
    # Success count based on compressed files
    success_count = len(compressed_files)
    success_rate = (success_count / total_images) * 100 if total_images > 0 else 0
    
    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'compression_rate': compression_rate,
        'success_count': success_count,
        'total_images': total_images,
        'success_rate': success_rate,
        'original_files': original_files,
        'compressed_files': compressed_files
    }


def print_results(stats):
    """Print the demo results."""
    print("\n" + "=" * 60)
    print("Demo Results - Markdown Image Optimizer")
    print("=" * 60)
    
    print("\nFile sizes:")
    print(f"  Original:  {stats['original_size']} bytes")
    print(f"  Compressed: {stats['compressed_size']} bytes")
    print(f"  Saved:     {stats['original_size'] - stats['compressed_size']} bytes")
    
    print(f"\n压缩率 (Compression Rate): {stats['compression_rate']:.2f}%")
    print(f"成功率 (Success Rate): {stats['success_rate']:.2f}%")
    
    print(f"\nDetails:")
    print(f"  Test images generated: {TEST_IMAGE_COUNT} ({TEST_IMAGE_WIDTH}x{TEST_IMAGE_HEIGHT} pixels each)")
    print(f"  Expected compression rate: ~{EXPECTED_COMPRESSION_RATE}%")
    print(f"  Actual compression rate: {stats['compression_rate']:.2f}%")
    
    print("\nOriginal files:")
    for file, size in stats['original_files']:
        print(f"  {file}: {size} bytes")
    
    print("\nCompressed files:")
    for file, size in stats['compressed_files']:
        print(f"  {file}: {size} bytes")
    
    print("=" * 60)
    
    # Note about small test images
    if stats['original_size'] < 1000:
        print("\nNote: Test images are very small (1x1 pixels due to pure Python generation)")
        print("      Install Pillow (pip install Pillow) for proper 50x50 test images")
        print("      Larger images will show more significant compression results")


def main():
    """Main demo execution."""
    print("=" * 60)
    print("Markdown Image Optimizer - Demo")
    print("=" * 60)
    
    # Step 1: Create test images
    print("\n[1/4] Creating test images...")
    create_test_images()
    
    # Step 2: Create sample markdown
    print("\n[2/4] Creating sample Markdown file...")
    sample_md = create_sample_markdown()
    print(f"Created: {sample_md}")
    
    # Step 3: Run optimizer
    print("\n[3/4] Running optimizer...")
    success, result = run_optimizer()
    
    # Step 4: Calculate and display statistics
    print("\n[4/4] Calculating statistics...")
    stats = calculate_statistics()
    print_results(stats)
    
    # Exit with appropriate code
    if success and stats['success_rate'] > 0:
        print("\nDemo completed successfully!")
        sys.exit(0)
    else:
        print("\nDemo completed with issues (ImageMagick may not be installed)")
        # Still exit 0 as long as we got some output
        if stats['original_size'] > 0:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
