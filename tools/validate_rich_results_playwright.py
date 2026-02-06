#!/usr/bin/env python
"""Validate rendered /events HTML using the web Rich Results Test via Playwright.

This is a fallback for cases where the Rich Results Test REST API is not available
for the project (404). The script opens the web UI, selects "Test code", pastes
the rendered HTML and runs the test, then extracts the textual results.

Requirements:
  pip install playwright jinja2
  playwright install

Usage:
  python tools/validate_rich_results_playwright.py --headless=false

Note: headful mode is recommended to observe the flow and handle any captcha or
consent UI. The script is best-effort — Google UI can change and selectors may
need adjustments.
"""
import os
import sys
import time
import argparse
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from playwright.sync_api import sync_playwright
except Exception:
    print(
        "Missing dependency playwright. Install with: pip install playwright && playwright install"
    )
    sys.exit(2)

TEMPLATES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates")
)
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


class _G:
    def __init__(self):
        self.csp_nonce = "PLAYWRIGHT_NONCE"


def render_events_html():
    template = env.get_template("events.html")

    def _csrf_token():
        return ""

    return template.render(
        g=_G(), url_for=lambda e, **k: "/" + e, csrf_token=_csrf_token, events=None
    )


def run_playwright(html, headless=True, slow_mo=50, dump_controls=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://search.google.com/test/rich-results", timeout=60000)
        time.sleep(1)

        # If requested, enumerate visible controls (buttons, tabs, links) and save to a file
        if dump_controls:
            try:
                elems = page.query_selector_all(
                    'button, [role="button"], [role="tab"], a, div[role="tab"]'
                )
                out_lines = []
                for e in elems:
                    try:
                        txt = e.inner_text().strip()
                    except Exception:
                        txt = ""
                    try:
                        aria = page.evaluate('(el)=>el.getAttribute("aria-label")', e)
                    except Exception:
                        aria = None
                    try:
                        role = page.evaluate('(el)=>el.getAttribute("role")', e)
                    except Exception:
                        role = None
                    line = f'TEXT: "{txt}" | ARIA: "{aria}" | ROLE: "{role}"'
                    out_lines.append(line)
                out_path = os.path.abspath(
                    os.path.join(
                        os.path.dirname(__file__), "..", "tmp_rich_controls.txt"
                    )
                )
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(out_lines))
                print("Wrote control texts to:", out_path)
            except Exception as exc:
                print("Failed to dump controls:", exc)
            finally:
                browser.close()
                return {"controls_file": out_path}

        # Try multiple localized labels for the "Test code" / "Code" UI
        test_buttons = [
            "text=/Test code/i",
            "text=/TEST CODE/i",
            "text=/Code/i",
            "text=/Код/i",
            "text=/КОД/i",
            "role=tab[name=/КОД/i]",
            "role=tab[name=/Code/i]",
            "text=/Проверить код/i",
            "text=/Проверить HTML/i",
        ]

        clicked = False
        for sel in test_buttons:
            try:
                locator = page.locator(sel).first
                if locator.count() > 0:
                    try:
                        locator.click()
                        clicked = True
                        print(f"Clicked code/test selector: {sel}")
                        break
                    except Exception:
                        # continue trying other selectors
                        pass
            except Exception:
                continue

        if not clicked:
            # If we couldn't click, enumerate candidate buttons/tabs to help debugging
            try:
                elems = page.query_selector_all(
                    'button, [role="button"], [role="tab"], a'
                )
                samples = []
                for e in elems[:40]:
                    try:
                        txt = e.inner_text().strip()
                        if txt:
                            samples.append(txt[:120])
                    except Exception:
                        continue
                print(
                    "Could not find Test code button automatically, opening page and waiting for manual paste..."
                )
                print("Nearby button/tab texts (sample):")
                for s in samples:
                    print(" -", s)
            except Exception:
                print("Could not enumerate page controls for debugging.")

        # Attempt to set the code into the editor. The Rich Results Test uses a code editor
        # (often CodeMirror) possibly inside an iframe. We'll try to set textarea/CodeMirror
        # in the main frame and all child frames via page.evaluate.
        set_code_script = """
        (html)=>{
            try {
                // Try simple textarea first
                var ta = document.querySelector('textarea');
                if (ta) { ta.focus(); ta.value = html; ta.dispatchEvent(new Event('input',{bubbles:true})); return true; }

                // Try CodeMirror instance
                var cmEl = document.querySelector('.CodeMirror');
                if (cmEl && cmEl.CodeMirror) { cmEl.CodeMirror.setValue(html); return true; }

                // Try editable divs (some editors use contenteditable)
                var editable = document.querySelector('[contenteditable="true"]');
                if (editable) { editable.focus(); editable.innerText = html; editable.dispatchEvent(new InputEvent('input',{bubbles:true})); return true; }

                return false;
            } catch (e) { return false; }
        }
        """

        set_ok = False
        try:
            # Try main frame
            set_ok = page.evaluate(set_code_script, html)
        except Exception:
            set_ok = False

        # Try child frames if main frame didn't work
        if not set_ok:
            try:
                for f in page.frames:
                    try:
                        ok = f.evaluate(set_code_script, html)
                        if ok:
                            set_ok = True
                            print("Set code inside a child frame.")
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if not set_ok:
            print(
                "Textarea/CodeMirror not found or could not be set programmatically. Trying additional heuristics..."
            )

            # Heuristic 1: search for likely editor containers by class/name and try to set innerText/value
            editor_candidates = [
                ".CodeMirror",
                ".ace_editor",
                ".monaco-editor",
                ".editor",
                ".source-editor",
                '[contenteditable="true"]',
                '[role="textbox"]',
                "textarea",
                'input[type="text"]',
            ]
            for sel in editor_candidates:
                try:
                    elems = page.query_selector_all(sel)
                    if not elems:
                        continue
                    for e in elems:
                        try:
                            # try setting .value
                            page.evaluate(
                                "(el, html)=>{ try{ el.value = html; el.innerText = html; el.textContent = html; return true;}catch(e){return false;} }",
                                e,
                                html,
                            )
                            # try specialized CodeMirror API on element
                            try:
                                page.evaluate(
                                    "(el, html)=>{ if(el.CodeMirror){ el.CodeMirror.setValue(html); return true; } return false; }",
                                    e,
                                    html,
                                )
                            except Exception:
                                pass
                            # focus and type as a fallback
                            try:
                                e.focus()
                                # type in chunks to avoid timeouts for very large HTML
                                chunk_size = 2000
                                for i in range(0, len(html), chunk_size):
                                    page.keyboard.type(html[i : i + chunk_size])
                                set_ok = True
                                print("Inserted HTML by focusing element matching", sel)
                                break
                            except Exception:
                                continue
                        except Exception:
                            continue
                    if set_ok:
                        break
                except Exception:
                    continue

        if not set_ok:
            # Heuristic 2: try typing directly into body (may activate editable region)
            try:
                page.focus("body")
                chunk_size = 2000
                for i in range(0, len(html), chunk_size):
                    page.keyboard.type(html[i : i + chunk_size])
                set_ok = True
                print("Inserted HTML by typing into page body")
            except Exception:
                set_ok = False

        if not set_ok:
            # As a last programmatic resort, inject a visible overlay textarea and populate it so user can copy/paste quickly
            try:
                inject_script = """
                (html)=>{
                    var id = 'playwright_inject';
                    var existing = document.getElementById(id);
                    if (existing) existing.remove();
                    var ta = document.createElement('textarea');
                    ta.id = id;
                    ta.style.position = 'fixed';
                    ta.style.right = '12px';
                    ta.style.top = '12px';
                    ta.style.width = '480px';
                    ta.style.height = '360px';
                    ta.style.zIndex = 2147483647;
                    ta.value = html;
                    document.body.appendChild(ta);
                    ta.focus();
                    return true;
                }
                """
                page.evaluate(inject_script, html)
                print(
                    "Injected overlay textarea with id playwright_inject. Please copy its contents into the Test code editor, then press Run."
                )
                print("Leaving browser open for 180 seconds...")
                time.sleep(180)
                browser.close()
                return None
            except Exception:
                print(
                    "Failed to inject overlay textarea; giving up and leaving the page for manual paste."
                )
                print("Leaving browser open for 120 seconds...")
                time.sleep(120)
                browser.close()
                return None

        # Try to ensure the underlying editor textarea (if present) receives the HTML
        try:
            # Prefer the named textarea used by the Google UI; set its value and dispatch events
            set_textarea = """(html)=>{
                try{
                    var ta = document.querySelector('textarea[jsname="bqeLof"]');
                    if(ta){ ta.focus(); ta.value = html; ta.dispatchEvent(new Event('input',{bubbles:true})); ta.dispatchEvent(new Event('change',{bubbles:true})); return true; }
                    // fallback: any CodeMirror textarea
                    var cmta = document.querySelector('.CodeMirror textarea');
                    if(cmta){ cmta.focus(); cmta.value = html; cmta.dispatchEvent(new Event('input',{bubbles:true})); cmta.dispatchEvent(new Event('change',{bubbles:true})); return true; }
                }catch(e){ /* ignore */ }
                return false;
            }"""
            try:
                ok = page.evaluate(set_textarea, html)
                if ok:
                    print(
                        'Set underlying textarea[jsname="bqeLof"] or CodeMirror textarea and dispatched input/change events.'
                    )
            except Exception:
                pass
        except Exception:
            pass

        # Robust Run-clicking: try several jsname-based buttons and poll for aria-disabled->false
        run_jsname_candidates = [
            'div[jsname="oe2Hje"]',
            'div[jsname="iyDKIb"]',
            'div[jsname="LZQqje"]',
            'div[jsname="oe2Hje"][role="button"]',
        ]
        clicked_run = False
        for sel in run_jsname_candidates:
            try:
                el = page.query_selector(sel)
                if not el:
                    continue
                # Poll until aria-disabled is not true (or timeout)
                for attempt in range(10):
                    try:
                        ad = page.evaluate('(el)=>el.getAttribute("aria-disabled")', el)
                    except Exception:
                        ad = None
                    # Consider both explicit 'false' and null/undefined as enabled
                    if ad in (None, "false"):
                        try:
                            el.click()
                            print("Clicked run button via selector:", sel)
                            clicked_run = True
                            break
                        except Exception:
                            try:
                                # direct JS click as fallback
                                page.evaluate("(el)=>el.click()", el)
                                print(
                                    "Clicked run button via JS click on selector:", sel
                                )
                                clicked_run = True
                                break
                            except Exception:
                                pass
                    time.sleep(0.4)
                if clicked_run:
                    break
            except Exception:
                continue

        if not clicked_run:
            # Last-resort: try text/button selectors
            run_buttons = [
                'button:has-text("Run test")',
                'button:has-text("RUN TEST")',
                'button:has-text("Run")',
                'button:has-text("Запустить тест")',
                'button:has-text("Проверить")',
                'button:has-text("Проверить код")',
                'button:has-text("ПРОВЕРИТЬ СТРАНИЦУ")',
            ]
            for rb in run_buttons:
                try:
                    if page.query_selector(rb):
                        try:
                            page.click(rb)
                            clicked_run = True
                            print("Clicked run button:", rb)
                            break
                        except Exception:
                            continue
                except Exception:
                    continue
        if not clicked_run:
            print(
                "Failed to click Run Test button automatically - you may need to press it manually."
            )

        # Wait for results to appear — look for results container
        try:
            page.wait_for_selector('div[role="main"]', timeout=60000)
        except Exception:
            pass

        # Take a full page screenshot for manual inspection
        out_png = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "tmp_rich_results.png")
        )
        page.screenshot(path=out_png, full_page=True)

        # Try to extract textual results
        try:
            # Issues and result text often appear inside elements with class 'result' or 'gsc-results'
            content = page.content()
        except Exception:
            content = None

        browser.close()
        return {"screenshot": out_png, "html": content}


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--headless",
        type=lambda s: s.lower() in ("1", "true", "yes"),
        default=False,
        help="Run browser headless",
    )
    p.add_argument(
        "--slow-mo", type=int, default=50, help="Slow motion ms for Playwright"
    )
    p.add_argument(
        "--dump-controls",
        action="store_true",
        help="Open page and dump nearby button/tab texts to tmp_rich_controls.txt",
    )
    args = p.parse_args()

    html = render_events_html()
    print("Rendered HTML length:", len(html))
    print("Launching browser, headless=" + str(args.headless))
    res = run_playwright(
        html,
        headless=args.headless,
        slow_mo=args.slow_mo,
        dump_controls=args.dump_controls,
    )
    if res is None:
        print("No automated result (manual interaction required).")
        sys.exit(2)
    print("Saved screenshot to:", res.get("screenshot"))
    # Optionally, write page html to file
    if res.get("html"):
        out_html = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "tmp_rich_results_page.html")
        )
        with open(out_html, "w", encoding="utf-8") as fh:
            fh.write(res["html"])
        print("Saved page HTML to:", out_html)


if __name__ == "__main__":
    main()
