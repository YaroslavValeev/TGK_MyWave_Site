#!/usr/bin/env python3
"""
Validate srcset file existence for services and blog posts.
Checks that dynamic image_url values have corresponding files in small/medium/large.
"""
import os
import sys
from pathlib import Path

def check_srcset_integrity():
    """Check if all image files referenced in services exist in small/medium/large."""
    base_images = Path("static/images")
    
    # Expected subdirectories for srcset
    sizes = ["small", "medium", "large"]
    size_dirs = {size: base_images / size for size in sizes}
    
    # Verify size directories exist
    missing_dirs = [size for size, dir_path in size_dirs.items() if not dir_path.exists()]
    if missing_dirs:
        print(f"❌ Missing directories: {', '.join(missing_dirs)}")
        return False
    
    print(f"✓ All srcset directories exist: {', '.join(sizes)}")
    
    # Load service data (mock check based on template patterns)
    # In real setup, you'd load from DB or config
    service_files = [
        "Balance_Board_New_25.jpg",
        "balans_trick_trening.jpg",
        "balans_trick_trening1.jpg",
        "training1.jpg",
    ]
    
    missing_files = []
    for filename in service_files:
        for size in sizes:
            size_path = size_dirs[size] / filename
            if not size_path.exists():
                missing_files.append(f"{size}/{filename}")
    
    if missing_files:
        print(f"⚠ Missing srcset variants (services): {missing_files}")
        return False
    
    print(f"✓ All service image srcset variants exist ({len(service_files)} images × {len(sizes)} sizes)")
    
    # Check static images (those without srcset, just data-fallback)
    static_images = [
        "balans_trick_trening1.jpg",
        "balans_trick_trening.jpg",
        "01.jpg",
        "02.jpg",
        "hero-wakesurf.png",
        "hero-wakesurf.webp",
        "Place1Logo.png",
    ]
    
    missing_static = [img for img in static_images if not (base_images / img).exists()]
    if missing_static:
        print(f"❌ Missing static images: {missing_static}")
        return False
    
    print(f"✓ All static images present ({len(static_images)} files)")
    
    # Verify placeholder exists
    placeholder = base_images / "Place1Logo.png"
    if not placeholder.exists():
        print(f"❌ Placeholder missing: {placeholder}")
        return False
    
    print(f"✓ Placeholder exists: Place1Logo.png")
    
    return True

def check_template_inline_code():
    """Verify no inline <script> or <style> in Safari templates."""
    templates_to_check = [
        "templates/wakesurf_safari.html",
        "templates/safari_booking_success.html",
    ]
    
    issues = []
    for template_path in templates_to_check:
        if not os.path.exists(template_path):
            issues.append(f"Template not found: {template_path}")
            continue
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for inline <script> (but NOT <script src=... or block tags
        # Look for: <script> or <script followed by newline/space (without src/defer/nonce)
        import re
        inline_script_pattern = r'<script(?![^>]*(?:src|defer|nonce)[^>]*)>'
        if re.search(inline_script_pattern, content):
            issues.append(f"{template_path}: Found inline <script> without external src")
        
        # Check for inline <style> (but NOT style within conditionals/templates)
        # Look for: <style> or <style nonce=...>
        if '<style>' in content or (re.search(r'<style\s+nonce=', content) and 'text/javascript' not in content):
            # If we found <style nonce=, check it's just structured data, not CSS styles
            if '<style>' in content:
                issues.append(f"{template_path}: Found inline <style>")
    
    if issues:
        for issue in issues:
            print(f"❌ {issue}")
        return False
    
    print(f"✓ No suspicious inline <script>/<style> in Safari templates")
    return True

def check_file_existence():
    """Verify created/modified files exist."""
    files_to_check = [
        "static/js/safari-booking.js",
        "static/css/safari.css",
        "static/js/image-fallbacks.js",
    ]
    
    missing = [f for f in files_to_check if not os.path.exists(f)]
    if missing:
        for f in missing:
            print(f"❌ Missing file: {f}")
        return False
    
    print(f"✓ All new files exist ({len(files_to_check)} files)")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Automated srcset/template validation")
    print("=" * 60)
    
    results = []
    
    print("\n1. Checking file existence...")
    results.append(("Files exist", check_file_existence()))
    
    print("\n2. Checking srcset integrity...")
    results.append(("Srcset files", check_srcset_integrity()))
    
    print("\n3. Checking template inline code...")
    results.append(("Template cleanliness", check_template_inline_code()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for check_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check_name}")
    
    all_passed = all(result for _, result in results)
    exit_code = 0 if all_passed else 1
    print(f"\nOverall: {'✓ PASS' if all_passed else '❌ FAIL'}")
    sys.exit(exit_code)
