#!/usr/bin/env python3
"""Read-only desktop/mobile interaction QA for the generated local HTML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def visible_cards(page) -> list[str]:
    return page.locator("article.paper:visible h3").all_text_contents()


def overflow_nodes(page) -> list[dict]:
    return page.evaluate(
        """() => [...document.querySelectorAll('body *')].filter(el => {
          const r=el.getBoundingClientRect();
          return r.right > innerWidth + 1 || r.left < -1;
        }).slice(0,20).map(el => ({tag:el.tagName, cls:el.className, right:el.getBoundingClientRect().right}))"""
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "index.html")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    report = args.report.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, object] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.goto(report.as_uri(), wait_until="load")
        page.locator("#panorama").scroll_into_view_if_needed()
        desktop = page.evaluate(
            """() => ({
              innerWidth,
              scrollWidth: document.documentElement.scrollWidth,
              cards: document.querySelectorAll('article.paper').length,
              notes: document.querySelectorAll('details.note').length,
              experiments: document.querySelectorAll('.experiment').length,
              panoramaNatural: [document.querySelector('#panorama img').naturalWidth, document.querySelector('#panorama img').naturalHeight],
              panoramaEmbedded: document.querySelector('#panorama img').src.startsWith('data:image/png;base64,')
            })"""
        )
        desktop["overflow"] = overflow_nodes(page)
        page.screenshot(path=output / "qa_desktop_panorama.png", full_page=False)

        page.locator("#open-panorama").click()
        page.wait_for_selector("#panorama-lightbox.open")
        evidence["lightbox_open"] = page.locator("#panorama-lightbox").evaluate(
            "(el) => el.classList.contains('open') && !!el.querySelector('img')"
        )
        page.screenshot(path=output / "qa_panorama_lightbox.png", full_page=False)
        page.locator("#close-panorama").click()

        page.locator("#q").fill("ACRouter")
        search_titles = visible_cards(page)
        page.locator("#q").fill("")
        page.locator("#theme").select_option(label="提示 / 反馈（4）")
        theme_titles = visible_cards(page)
        page.locator("#theme").select_option("")
        page.locator("details.note").first.evaluate("(el) => el.open = true")
        desktop_expanded_overflow = overflow_nodes(page)

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        mobile.goto(report.as_uri(), wait_until="load")
        mobile.locator("#panorama").scroll_into_view_if_needed()
        mobile_data = mobile.evaluate(
            """() => ({
              innerWidth,
              scrollWidth: document.documentElement.scrollWidth,
              panoramaWidth: document.querySelector('#panorama img').getBoundingClientRect().width,
              panoramaEmbedded: document.querySelector('#panorama img').src.startsWith('data:image/png;base64,')
            })"""
        )
        mobile_data["overflow"] = overflow_nodes(mobile)
        mobile.screenshot(path=output / "qa_mobile_panorama.png", full_page=False)
        mobile.locator("#q").fill("ACRouter")
        mobile_search_titles = visible_cards(mobile)
        mobile.locator("details.note").first.evaluate("(el) => el.open = true")
        mobile_data["expanded_overflow"] = overflow_nodes(mobile)
        browser.close()

    evidence.update(
        {
            "report": report.name,
            "desktop": desktop,
            "search_acrouter": search_titles,
            "theme_prompt_feedback": theme_titles,
            "desktop_expanded_overflow": desktop_expanded_overflow,
            "mobile": mobile_data,
            "mobile_search_acrouter": mobile_search_titles,
        }
    )
    assertions = {
        "desktop_no_horizontal_overflow": desktop["innerWidth"] == desktop["scrollWidth"] and not desktop["overflow"],
        "mobile_no_horizontal_overflow": mobile_data["innerWidth"] == mobile_data["scrollWidth"] and not mobile_data["overflow"],
        "expanded_content_no_overflow": not desktop_expanded_overflow and not mobile_data["expanded_overflow"],
        "panorama_embedded_3600x3320": desktop["panoramaEmbedded"] and desktop["panoramaNatural"] == [3600, 3320],
        "lightbox_click_opens": evidence["lightbox_open"] is True,
        "search_acrouter_one": len(search_titles) == 1 and len(mobile_search_titles) == 1,
        "theme_filter_four": len(theme_titles) == 4,
        "structure_counts": desktop["cards"] == 41 and desktop["notes"] == 8 and desktop["experiments"] == 3,
    }
    evidence["assertions"] = assertions
    (output / "visual_qa.log").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if not all(assertions.values()):
        raise SystemExit("visual QA failed")


if __name__ == "__main__":
    main()
