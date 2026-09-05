#!/usr/bin/env python3
"""
Markdown Image Optimizer - Local Markdown image automatic compression and path conversion tool.
Prioritizes using system ImageMagick (convert/magick) for compression.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


class ImageMagickChecker:
    """Check if ImageMagick is installed on the system."""
    
    @staticmethod
    def check() -> tuple[bool, str]:
        """Check if ImageMagick is available. Returns (available, command)."""
        # Try 'magick' first (ImageMagick 7+), then 'convert' (ImageMagick 6)
        for cmd in ['magick', 'convert']:
            try:
                result = subprocess.run(
                    [cmd, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True, cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return False, ''
    
    @staticmethod
    def get_version() -> str:
        """Get ImageMagick version string."""
        available, cmd = ImageMagickChecker.check()
        if available:
            try:
                result = subprocess.run(
                    [cmd, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.stdout.strip().split('\n')[0]
            except Exception:
                return "Not installed"
        return "Not installed"


class MarkdownImageProcessor:
    """Process Markdown files and optimize embedded images."""
    
    # Regex patterns for Markdown image syntax
    IMAGE_PATTERN = re.compile(
        r'!\[([^\]]*)\]\(([^\)]+)\)',
        re.MULTILINE | re.UNICODE
    )
    
    def __init__(
        self,
        input_path: str,
        output_path: str,
        quality: int = 80,
        max_width: int = 1920,
        imagemagick_cmd: str = None
    ):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.quality = max(1, min(100, quality))
        self.max_width = max_width
        self.imagemagick_cmd = imagemagick_cmd or 'convert'
        
        # Statistics
        self.processed_files = 0
        self.processed_images = 0
        self.compressed_images = 0
        self.failed_images = 0
        self.total_original_size = 0
        self.total_compressed_size = 0
        self.image_counter = 300  # Start numbering from 300
        
        # Error tracking
        self.errors = []
    
    def escape_path(self, path: str) -> str:
        """Escape paths with Chinese characters or spaces for ImageMagick."""
        # Quote the path if it contains spaces or non-ASCII characters
        if any(c in path for c in ' \t\n\r!@#$%^&*()[]{}|;\'"\\'):
            # Use shlex.quote equivalent for Windows compatibility
            if sys.platform == 'win32':
                return f'"{path}"'
            else:
                # Escape backslashes first, then single quotes
                escaped = path.replace('\\', '\\\\')
                escaped = escaped.replace("'", "'\\''")
                return f"'{escaped}'"
        return path
    
    def extract_images(self, markdown_content: str) -> list[tuple[str, str, str]]:
        """Extract all image references from Markdown content.
        
        Returns list of tuples: (alt_text, path, full_match)
        """
        images = []
        for match in self.IMAGE_PATTERN.finditer(markdown_content):
            alt_text = match.group(1) or ''
            path = match.group(2)
            full_match = match.group(0)
            images.append((alt_text, path, full_match))
        return images
    
    def is_absolute_url(self, path: str) -> bool:
        """Check if path is a URL."""
        return path.startswith(('http://', 'https://', 'ftp://'))
    
    def resolve_image_path(self, image_path: str, markdown_file: Path) -> Optional[Path]:
        """Resolve image path relative to markdown file location."""
        if self.is_absolute_url(image_path):
            return None
        
        path = Path(image_path)
        
        # If already absolute, return as-is
        if path.is_absolute():
            return path if path.exists() else None
        
        # Resolve relative to markdown file directory
        resolved = (markdown_file.parent / path).resolve()
        return resolved if resolved.exists() else None
    
    def compress_image(
        self,
        input_image: Path,
        output_image: Path,
        original_size: int
    ) -> tuple[bool, int]:
        """Compress a single image using ImageMagick.
        
        Returns: (success, new_size)
        """
        try:
            # Ensure output directory exists
            output_image.parent.mkdir(parents=True, exist_ok=True)
            
            # Build ImageMagick command
            # Use -resize with > to only shrink larger images, not enlarge smaller ones
            # Format: convert input -resize 'WIDTHx>' -quality Q output
            cmd = [
                self.imagemagick_cmd,
                str(input_image),
                '-resize',
                f'{self.max_width}x>',
                '-quality',
                str(self.quality),
                str(output_image)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and output_image.exists():
                new_size = output_image.stat().st_size
                self.total_original_size += original_size
                self.total_compressed_size += new_size
                return True, new_size
            else:
                self.errors.append(
                    f"ImageMagick failed for {input_image}: {result.stderr}"
                )
                return False, original_size
                
        except subprocess.TimeoutExpired:
            self.errors.append(f"Timeout compressing {input_image}")
            return False, original_size
        except Exception as e:
            self.errors.append(f"Error compressing {input_image}: {str(e)}")
            return False, original_size
    
    def process_markdown_file(self, md_file: Path) -> tuple[str, bool]:
        """Process a single Markdown file.
        
        Returns: (new_content, success)
        """
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"Error reading {md_file}: {e}")
            return '', False
        
        images = self.extract_images(content)
        if not images:
            return content, True
        
        new_content = content
        replaced_paths = {}
        
        for alt_text, path, full_match in images:
            # Skip URLs
            if self.is_absolute_url(path):
                continue
            
            # Resolve actual image file
            image_path = self.resolve_image_path(path, md_file)
            if not image_path or not image_path.exists():
                continue
            
            # Generate new image name with numbering starting from 300
            ext = image_path.suffix.lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                ext = '.jpg'  # Default to jpg for conversion
            
            new_image_name = f"img_{self.image_counter}{ext}"
            new_image_path = self.output_path / new_image_name
            self.image_counter += 1
            
            # Get original file size
            original_size = image_path.stat().st_size
            
            # Compress image
            success, new_size = self.compress_image(image_path, new_image_path, original_size)
            self.processed_images += 1
            
            if success:
                self.compressed_images += 1
                # Calculate relative path from output markdown location
                rel_path = os.path.relpath(new_image_path, self.output_path)
                rel_path = rel_path.replace('\\', '/')  # Normalize for cross-platform
                replaced_paths[full_match] = f"![{alt_text}]({rel_path})"
            else:
                self.failed_images += 1
                # Keep original path on failure
        
        # Replace all image paths in content
        for old_match, new_match in replaced_paths.items():
            new_content = new_content.replace(old_match, new_match)
        
        return new_content, True
    
    def process(self) -> dict:
        """Process input (file or directory) and generate optimized output."""
        results = {
            'files_processed': 0,
            'images_found': 0,
            'images_compressed': 0,
            'images_failed': 0,
            'compression_rate': 0.0,
            'output_files': []
        }
        
        # Ensure output directory exists
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Collect markdown files
        if self.input_path.is_file():
            if self.input_path.suffix.lower() == '.md':
                md_files = [self.input_path]
            else:
                print(f"Warning: {self.input_path} is not a Markdown file")
                md_files = []
        elif self.input_path.is_dir():
            md_files = list(self.input_path.glob('**/*.md'))
        else:
            print(f"Error: Input path does not exist: {self.input_path}")
            return results
        
        # Process each markdown file
        for md_file in md_files:
            new_content, success = self.process_markdown_file(md_file)
            
            if success:
                # Write output markdown file
                output_md = self.output_path / md_file.name
                with open(output_md, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                self.processed_files += 1
                results['files_processed'] += 1
                results['output_files'].append(str(output_md))
        
        # Calculate compression rate
        results['images_found'] = self.processed_images
        results['images_compressed'] = self.compressed_images
        results['images_failed'] = self.failed_images
        
        if self.total_original_size > 0:
            results['compression_rate'] = (
                (self.total_original_size - self.total_compressed_size) 
                / self.total_original_size * 100
            )
        
        return results
    
    def print_report(self, results: dict):
        """Print processing report."""
        print("\n" + "=" * 50)
        print("Markdown Image Optimizer - Processing Report")
        print("=" * 50)
        print(f"Files processed:     {results['files_processed']}")
        print(f"Images found:        {results['images_found']}")
        print(f"Images compressed:   {results['images_compressed']}")
        print(f"Images failed:       {results['images_failed']}")
        print(f"Compression rate:    {results['compression_rate']:.2f}%")
        print(f"Space saved:         {self.total_original_size - self.total_compressed_size} bytes")
        print("-" * 50)
        
        if self.errors:
            print("Errors encountered:")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
        
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='Markdown Image Optimizer - Compress images in Markdown files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --input ./docs --output ./optimized --quality 80 --max-width 1920
  %(prog)s --input README.md --output ./output
        '''
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input Markdown file or directory containing Markdown files'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory for optimized Markdown files and images'
    )
    
    parser.add_argument(
        '--quality', '-q',
        type=int,
        default=80,
        help='JPEG compression quality (1-100, default: 80)'
    )
    
    parser.add_argument(
        '--max-width', '-w',
        type=int,
        default=1920,
        help='Maximum image width in pixels (default: 1920)'
    )
    
    args = parser.parse_args()
    
    # Check ImageMagick availability
    available, cmd = ImageMagickChecker.check()
    if not available:
        print("Error: ImageMagick is not installed on this system.")
        print("Please install ImageMagick:")
        print("  Ubuntu/Debian: sudo apt-get install imagemagick")
        print("  macOS: brew install imagemagick")
        print("  Windows: Download from https://imagemagick.org/script/download.php")
        sys.exit(1)
    
    print(f"ImageMagick detected: {cmd}")
    
    # Create processor and run
    processor = MarkdownImageProcessor(
        input_path=args.input,
        output_path=args.output,
        quality=args.quality,
        max_width=args.max_width,
        imagemagick_cmd=cmd
    )
    
    results = processor.process()
    processor.print_report(results)
    
    # Exit with appropriate code
    if results['images_failed'] > 0 and results['images_compressed'] == 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
