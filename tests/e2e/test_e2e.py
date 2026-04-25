"""
E2E tests — Playwright (Python).
Run with:  pytest tests/e2e/ -v --headed
Requires:  pip install playwright && playwright install chromium
"""
import re
import pytest
from playwright.sync_api import Page, expect


CONSOLE_URL = "http://localhost:3000"


@pytest.fixture(scope="session")
def browser_context_args():
    return {"ignore_https_errors": True}


# ── Console navigation ────────────────────────────────────────────────────

def test_console_loads(page: Page):
    page.goto(CONSOLE_URL)
    expect(page.locator("nav")).to_be_visible()
    expect(page.locator("h1")).to_contain_text("Overview")


def test_nav_links_work(page: Page):
    page.goto(CONSOLE_URL)
    for link_text, heading in [
        ("Run Agent", "Run Agent"),
        ("Documents", "Documents"),
        ("Workflows", "Workflows"),
        ("LLM Activity", "LLM Activity"),
        ("Observability", "Observability"),
        ("Marketplace", "Marketplace"),
        ("Admin", "Admin"),
    ]:
        page.get_by_role("link", name=re.compile(link_text)).click()
        expect(page.locator("h1")).to_contain_text(heading)


# ── Run Agent page ─────────────────────────────────────────────────────────

def test_run_agent_submit(page: Page):
    page.goto(f"{CONSOLE_URL}/run-agent")
    page.fill("#prompt", "What is 2 + 2?")
    page.click("#sendBtn")
    # Wait for response card to appear
    page.wait_for_selector("#result-card", state="visible", timeout=120000)
    response_text = page.text_content("#response")
    assert response_text != "Thinking..."


# ── Marketplace ────────────────────────────────────────────────────────────

def test_marketplace_shows_templates(page: Page):
    page.goto(f"{CONSOLE_URL}/marketplace")
    page.wait_for_selector(".card button", timeout=10000)
    cards = page.locator("#templates .card")
    assert cards.count() > 0


def test_marketplace_search(page: Page):
    page.goto(f"{CONSOLE_URL}/marketplace")
    page.wait_for_selector("#templates .card", timeout=10000)
    page.fill("#search", "web")
    page.wait_for_timeout(500)
    cards = page.locator("#templates .card")
    assert cards.count() >= 1


# ── Dashboard ──────────────────────────────────────────────────────────────

def test_dashboard_loads(page: Page):
    page.goto(CONSOLE_URL)
    expect(page.locator("body")).to_be_visible()
    expect(page.locator("h1")).to_contain_text("Overview")


# ── Documents page ─────────────────────────────────────────────────────────

def test_documents_page_loads(page: Page):
    page.goto(f"{CONSOLE_URL}/documents")
    expect(page.locator("h1")).to_contain_text("Documents")


# ── Admin page ─────────────────────────────────────────────────────────────

def test_admin_shows_features(page: Page):
    page.goto(f"{CONSOLE_URL}/admin")
    expect(page.locator("h1")).to_contain_text("Admin")
    # ChromaDB should show as Enabled (Core)
    page.wait_for_selector("text=ChromaDB", timeout=5000)
    expect(page.locator("text=Enabled (Core)")).to_be_visible()
