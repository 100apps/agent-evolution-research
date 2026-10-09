#!/usr/bin/env python3
"""Optional local Edge check for the standalone public trend page."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def inspect(page) -> dict:
    return page.evaluate("""() => ({
      width: innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      chartPoints: document.querySelectorAll('#plot circle').length,
      tableRows: document.querySelectorAll('#heat tr').length,
      title: document.title,
      trendDisclaimer: document.body.textContent.includes('不是研究人员人数'),
      repositoryLink: !!document.querySelector('a[href*="/tree/main/research_trends"]')
    })""")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = args.report.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        desktop = browser.new_page(viewport={"width": 1440, "height": 1000})
        desktop.goto(report.as_uri(), wait_until="load")
        desktop_before = inspect(desktop)
        desktop.locator("#metric").select_option("ax:core_ai_5_share_all_pct")
        desktop.locator("#cohort").select_option("ACL")
        desktop_after = inspect(desktop)
        desktop.screenshot(path=output / "trends_desktop.png", full_page=True)
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        mobile.goto(report.as_uri(), wait_until="load")
        mobile_state = inspect(mobile)
        mobile.screenshot(path=output / "trends_mobile.png", full_page=True)
        browser.close()
    checks = {
        "desktop_no_page_overflow": desktop_after["documentWidth"] <= desktop_after["width"] + 1,
        "mobile_no_page_overflow": mobile_state["documentWidth"] <= mobile_state["width"] + 1,
        "monthly_points": desktop_before["chartPoints"] == desktop_after["chartPoints"] == mobile_state["chartPoints"] == 81,
        "conference_table": desktop_after["tableRows"] >= 18,
        "disclaimer_and_source": mobile_state["trendDisclaimer"] and mobile_state["repositoryLink"],
    }
    result = {"report": str(report), "desktop_before": desktop_before,
              "desktop_after": desktop_after, "mobile": mobile_state, "checks": checks}
    (output / "visual_qa.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
