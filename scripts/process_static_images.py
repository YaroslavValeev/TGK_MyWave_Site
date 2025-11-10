"""Script to process all existing images in the static/images folder and create resized versions."""
import os
import sys
from PIL import Image
import shutil
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.images_service import SIZES, ALLOWED_EXTENSIONS

def process_images(source_dir, dest_dir):
    """Process all images in the source directory and create resized versions."""
    # Create destination directory if it doesn't exist
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    
    # Create size directories
    for size in SIZES.keys():
        Path(os.path.join(dest_dir, size)).mkdir(parents=True, exist_ok=True)
    
    # Process all files
    for root, _, files in os.walk(source_dir):
        for filename in files:
            if not any(filename.lower().endswith(f".{ext}") for ext in ALLOWED_EXTENSIONS):
                continue
                
            source_path = os.path.join(root, filename)
            relative_path = os.path.relpath(source_path, source_dir)
            dest_path = os.path.join(dest_dir, relative_path)
            
            # Create destination subdirectory if needed
            Path(os.path.dirname(dest_path)).mkdir(parents=True, exist_ok=True)
            
            # Copy original file
            shutil.copy2(source_path, dest_path)
            
            try:
                # Create resized versions
                with Image.open(source_path) as img:
                    for size_name, dimensions in SIZES.items():
                        size_path = os.path.join(dest_dir, size_name, relative_path)
                        Path(os.path.dirname(size_path)).mkdir(parents=True, exist_ok=True)
                        
                        # Create resized copy
                        copy = img.copy()
                        copy.thumbnail(dimensions)
                        copy.save(size_path, optimize=True, quality=85)
                        
                print(f"Processed: {relative_path}")
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
    source_images = os.path.join(static_dir, 'images')
    dest_images = os.path.join(static_dir, 'images_processed')
    
    print("Starting image processing...")
    process_images(source_images, dest_images)
    print("Image processing complete!")
    print(f"Processed images are in: {dest_images}")
    print("Review the processed images and if satisfied, replace the contents of static/images with static/images_processed")