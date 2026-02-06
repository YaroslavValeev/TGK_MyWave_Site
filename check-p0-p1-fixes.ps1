# ============================================================================
# QA CHECK SCRIPT: P0/P1 Hotfixes Validation
# ============================================================================
# Проверяет выполнение требований P0.1, P0.2, P0.3, P1.1, P1.2, P1.3
# ============================================================================

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  QA CHECK: P0/P1 HOTFIXES (CSP, Images, srcset, A11y)" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$basePath = Get-Location
$templatesPath = "$basePath/templates"
$staticPath = "$basePath/static"
$cssPath = "$staticPath/css"

$passCount = 0
$failCount = 0
$warnCount = 0

# ============================================================================
# P0.1: INLINE-ZERO (no onclick, onerror, onload handlers)
# ============================================================================
Write-Host "[P0.1] INLINE-ZERO CHECK" -ForegroundColor Yellow

$inlinePatterns = @(
    'onerror\s*=',
    'onclick\s*=',
    'onload\s*=',
    'onmouseover\s*=',
    'onchange\s*=',
    'onsubmit\s*='
)

$inlineMatches = @()
foreach ($pattern in $inlinePatterns) {
    $matches = Get-ChildItem -Recurse -Path $templatesPath -Include "*.html" | 
        Select-String -Pattern $pattern -ErrorAction SilentlyContinue
    $inlineMatches += $matches
}

# Filter out allowed patterns (like reader.onload in JS)
$inlineMatches = $inlineMatches | Where-Object { $_ -notmatch '\.onload\s*=|\.onerror\s*=' }

if ($inlineMatches.Count -eq 0) {
    Write-Host "  ✅ PASS: No inline event handlers found in templates" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "  ❌ FAIL: Found inline event handlers:" -ForegroundColor Red
    $inlineMatches | ForEach-Object { 
        Write-Host "    - $($_.Filename):$($_.LineNumber) → $($_.Line.Trim())" -ForegroundColor Red
    }
    $failCount++
}
Write-Host ""

# ============================================================================
# P0.2: CSP - Check Safari pages for orphan styles/scripts
# ============================================================================
Write-Host "[P0.2] CSP SAFARI CHECK" -ForegroundColor Yellow

$safariFiles = @(
    "$templatesPath/wakesurf_safari.html",
    "$templatesPath/safari_booking_success.html"
)

$cssOrphanFound = $false
$inlineScriptFound = $false

foreach ($file in $safariFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        
        # Check for orphan styles (CSS outside block tags)
        if ($content -match '(?<!</style>)\.\w+\s*{[\s\S]*?}(?!.*</style>)' -and -not ($content -match '<style')) {
            Write-Host "  ⚠️  WARNING: Potential orphan CSS in $([System.IO.Path]::GetFileName($file))" -ForegroundColor Yellow
            $warnCount++
            $cssOrphanFound = $true
        }
        
        # Check for inline script blocks (should use <script defer src="...">)
        if ($content -match '<script[^>]*>\s*(?!.*defer)' -and $content -match '\.js' -eq $false) {
            # This is a simplified check; actual inline scripts would have code between tags
            $inlineScripts = [regex]::Matches($content, '<script[^>]*>([^<]+)</script>')
            if ($inlineScripts.Count -gt 0) {
                Write-Host "  ⚠️  WARNING: Found inline script blocks in $([System.IO.Path]::GetFileName($file))" -ForegroundColor Yellow
                $warnCount++
                $inlineScriptFound = $true
            }
        }
    }
}

if (-not $cssOrphanFound -and -not $inlineScriptFound) {
    Write-Host "  ✅ PASS: Safari pages appear CSP-clean (external CSS/JS only)" -ForegroundColor Green
    $passCount++
}
Write-Host ""

# ============================================================================
# P0.3: IMAGE FALLBACK - Check data-fallback on key pages
# ============================================================================
Write-Host "[P0.3] IMAGE FALLBACK CHECK" -ForegroundColor Yellow

$keyPages = @(
    "$templatesPath/index.html",
    "$templatesPath/services.html",
    "$templatesPath/projects.html",
    "$templatesPath/shop.html",
    "$templatesPath/blog/index.html"
)

$missingFallback = @()
$missingDimensions = @()

foreach ($page in $keyPages) {
    if (Test-Path $page) {
        $content = Get-Content $page -Raw
        $imgTags = [regex]::Matches($content, '<img[^>]*>')
        
        foreach ($img in $imgTags) {
            $imgStr = $img.Value
            
            # Check for data-fallback
            if ($imgStr -notmatch 'data-fallback') {
                $missingFallback += "  - $([System.IO.Path]::GetFileName($page)): Missing data-fallback"
            }
            
            # Check for width/height (CLS prevention)
            if ($imgStr -notmatch '(width|height)=') {
                $missingDimensions += "  - $([System.IO.Path]::GetFileName($page)): Missing width/height"
            }
        }
    }
}

if ($missingFallback.Count -eq 0 -and $missingDimensions.Count -eq 0) {
    Write-Host "  ✅ PASS: All key images have data-fallback and dimensions" -ForegroundColor Green
    $passCount++
} else {
    if ($missingFallback.Count -gt 0) {
        Write-Host "  ⚠️  WARNING: Images without data-fallback:" -ForegroundColor Yellow
        $missingFallback | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
        $warnCount++
    }
    if ($missingDimensions.Count -gt 0) {
        Write-Host "  ⚠️  WARNING: Images without width/height:" -ForegroundColor Yellow
        $missingDimensions | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
        $warnCount++
    }
}
Write-Host ""

# ============================================================================
# P1.1: SRCSET GATE - Check for fake srcset
# ============================================================================
Write-Host "[P1.1] SRCSET GATE CHECK" -ForegroundColor Yellow

$fakeSrcsetFound = @()

foreach ($page in $keyPages) {
    if (Test-Path $page) {
        $content = Get-Content $page -Raw
        
        # Check for srcset pointing to non-existent directories (small/, medium/, large/)
        $fakeSrcsets = [regex]::Matches($content, 'srcset="[^"]*(?:small|medium|large)/[^"]*"')
        
        foreach ($srcset in $fakeSrcsets) {
            $fakeSrcsetFound += "  - $([System.IO.Path]::GetFileName($page)): $($srcset.Value)"
        }
    }
}

if ($fakeSrcsetFound.Count -eq 0) {
    Write-Host "  ✅ PASS: No fake srcset paths found (small/medium/large)" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "  ❌ FAIL: Found fake srcset paths:" -ForegroundColor Red
    $fakeSrcsetFound | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    $failCount++
}
Write-Host ""

# ============================================================================
# P1.2: BLOG CARD A11y - Check :focus-within CSS
# ============================================================================
Write-Host "[P1.2] BLOG CARD A11y CHECK" -ForegroundColor Yellow

$styleContent = Get-Content "$cssPath/style.css" -Raw

if ($styleContent -match '\.blog-card:focus-within') {
    Write-Host "  ✅ PASS: .blog-card:focus-within CSS found" -ForegroundColor Green
    $passCount++
} else {
    Write-Host "  ❌ FAIL: .blog-card:focus-within CSS not found" -ForegroundColor Red
    $failCount++
}
Write-Host ""

# ============================================================================
# P1.3: SHOP FILTERS - Check aria-pressed logic
# ============================================================================
Write-Host "[P1.3] SHOP FILTERS A11y CHECK" -ForegroundColor Yellow

$shopFilterFile = "$staticPath/js/shop-filter.js"
if (Test-Path $shopFilterFile) {
    $jsContent = Get-Content $shopFilterFile -Raw
    
    if ($jsContent -match 'aria-pressed' -and $jsContent -match 'setAttribute.*aria-pressed') {
        Write-Host "  ✅ PASS: filter buttons use aria-pressed attribute" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "  ❌ FAIL: aria-pressed logic not found in shop-filter.js" -ForegroundColor Red
        $failCount++
    }
} else {
    Write-Host "  ⚠️  WARNING: shop-filter.js not found" -ForegroundColor Yellow
    $warnCount++
}
Write-Host ""

# ============================================================================
# BONUS: ui-actions.js check
# ============================================================================
Write-Host "[BONUS] UI-ACTIONS.JS CHECK" -ForegroundColor Yellow

$uiActionsFile = "$staticPath/js/ui-actions.js"
if (Test-Path $uiActionsFile) {
    $content = Get-Content $uiActionsFile -Raw
    
    if ($content -match 'data-action' -and $content -match 'window.print' -and $content -match 'bootstrap.Modal') {
        Write-Host "  ✅ PASS: ui-actions.js correctly handles data-action handlers" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "  ⚠️  WARNING: ui-actions.js may be incomplete" -ForegroundColor Yellow
        $warnCount++
    }
} else {
    Write-Host "  ❌ FAIL: ui-actions.js not found (required for P0.1)" -ForegroundColor Red
    $failCount++
}
Write-Host ""

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Write-Host ""
Write-Host "  ✅ PASSED: $passCount" -ForegroundColor Green
Write-Host "  ❌ FAILED: $failCount" -ForegroundColor Red
Write-Host "  ⚠️  WARNINGS: $warnCount" -ForegroundColor Yellow
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "  🎉 ALL CRITICAL CHECKS PASSED! Ready for manual QA." -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Please fix failing checks before manual QA." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# MANUAL QA INSTRUCTIONS
# ============================================================================
Write-Host "📋 NEXT STEPS: Manual QA" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Start server: python main.py" -ForegroundColor White
Write-Host "2. Open browser pages and check:" -ForegroundColor White
Write-Host "   • http://localhost:5000/wakesurf-safari (Print button, no CSP errors)" -ForegroundColor Gray
Write-Host "   • http://localhost:5000/shop (Filters aria-pressed, DevTools check)" -ForegroundColor Gray
Write-Host "   • http://localhost:5000/blog (Tab to cards, :focus-within visible)" -ForegroundColor Gray
Write-Host "3. DevTools Network: Check for 404 images on each key page" -ForegroundColor White
Write-Host "4. DevTools Console: Verify 0 CSP violations" -ForegroundColor White
Write-Host ""
