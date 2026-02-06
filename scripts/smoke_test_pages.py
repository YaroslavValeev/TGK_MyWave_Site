#!/usr/bin/env python3
"""
Quick smoke test: check HTTP status codes and CSP headers for P1 pages.
Requires Flask to be running on http://127.0.0.1:5000
"""
import requests
import sys
import json
from datetime import datetime

TARGET_PAGES = [
    "/",  # index
    "/wakesurf-safari",  # safari form
    "/wakesurf-safari/booking-success?id=test",  # safari success
    "/services",  # services with srcset
    "/projects",  # projects 
    "/shop",  # shop with filters
    "/blog",  # blog list
]

def check_page(url):
    """Check HTTP status and CSP header."""
    full_url = f"http://127.0.0.1:5000{url}"
    try:
        resp = requests.get(full_url, timeout=5)
        status = resp.status_code
        csp = resp.headers.get("Content-Security-Policy", "")
        
        # Check for critical CSP violations
        has_inline_script_violation = "'unsafe-inline'" in csp and "script-src" in csp.split("'unsafe-inline'")[0]
        
        return {
            "url": url,
            "status": status,
            "ok": 200 <= status < 300,
            "csp_present": bool(csp),
            "csp_length": len(csp),
            "inline_script_allowed": has_inline_script_violation,  # Bad if true
            "error": None
        }
    except Exception as e:
        return {
            "url": url,
            "status": None,
            "ok": False,
            "error": str(e)
        }

def main():
    print("=" * 70)
    print(f"HTTP Smoke Test for P1.0–P1.4 Pages ({datetime.now().isoformat()})")
    print("=" * 70)
    print("\nChecking Flask on http://127.0.0.1:5000\n")
    
    results = []
    for page_url in TARGET_PAGES:
        result = check_page(page_url)
        results.append(result)
        
        if result["error"]:
            print(f"❌ {page_url}")
            print(f"   Error: {result['error']}")
        else:
            status_icon = "✓" if result["ok"] else "❌"
            print(f"{status_icon} {page_url} → HTTP {result['status']}")
            if result["csp_present"]:
                print(f"   CSP: {result['csp_length']} chars")
                if result["inline_script_allowed"]:
                    print(f"   ⚠ WARNING: CSP allows 'unsafe-inline' for scripts (check inline JS)")
            else:
                print(f"   ⚠ WARNING: No CSP header found!")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    
    passed = sum(1 for r in results if r.get("ok", False))
    total = len(results)
    failed = [r for r in results if not r.get("ok", True)]
    
    print(f"✓ Pages loaded: {passed}/{total}")
    
    if failed:
        print(f"\n❌ Failed pages:")
        for r in failed:
            print(f"  - {r['url']}: {r.get('error') or f'HTTP {r.get(\"status\")}'}")
    
    has_csp_issues = any(r.get("inline_script_allowed") for r in results)
    if has_csp_issues:
        print(f"\n⚠ CSP inline-script issues detected (see above)")
    
    exit_code = 0 if (passed == total and not has_csp_issues) else 1
    print(f"\nOverall: {'✓ PASS' if exit_code == 0 else '❌ FAIL'}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
