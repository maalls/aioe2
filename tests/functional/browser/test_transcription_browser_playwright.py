import pytest


@pytest.mark.django_db(transaction=True)
def test_transcription_browser_renders_viewer_panel(live_server, browser_page, browser_output_root):
    """Smoke test: transcription browser page renders viewer panel in a real browser."""
    folder = browser_output_root["folder_name"]
    browser_page.goto(
        f"{live_server.url}/transcription/?folder={folder}",
        wait_until="domcontentloaded",
    )

    assert browser_page.locator("#viewer-panel").count() == 1
    assert browser_page.locator("#timeline-sync-root").count() == 1
    assert browser_page.locator("#preview-player").count() == 1
    assert "Transcription Viewer" in browser_page.title()


@pytest.mark.django_db(transaction=True)
def test_toggle_sync_changes_linked_state(live_server, browser_page, browser_output_root):
    folder = browser_output_root["folder_name"]
    browser_page.goto(f"{live_server.url}/transcription/?folder={folder}", wait_until="domcontentloaded")

    sync_button = browser_page.locator(".sync-toggle").first
    assert sync_button.get_attribute("data-sync-linked") == "1"

    sync_button.click()
    assert sync_button.get_attribute("data-sync-linked") == "0"
    assert browser_page.locator("#timeline-sync-root").get_attribute("data-sync-linked") == "0"


@pytest.mark.django_db(transaction=True)
def test_star_filter_hides_non_bookmarked_segments(live_server, browser_page, browser_output_root):
    folder = browser_output_root["folder_name"]
    browser_page.goto(f"{live_server.url}/transcription/?folder={folder}", wait_until="domcontentloaded")

    segments = browser_page.locator("[data-segment-item='1']")
    assert segments.count() >= 2

    browser_page.locator(".star-filter-toggle").first.click()

    hidden_segments = browser_page.locator("[data-segment-item='1'].hidden")
    assert hidden_segments.count() >= 1


@pytest.mark.django_db(transaction=True)
def test_click_segment_seeks_player(live_server, browser_page, browser_output_root):
    folder = browser_output_root["folder_name"]
    browser_page.goto(f"{live_server.url}/transcription/?folder={folder}", wait_until="domcontentloaded")

    browser_page.locator("[data-segment-item='1'][data-start^='6']").first.click()
    current_time = browser_page.eval_on_selector("#preview-player", "el => el.currentTime")

    assert current_time >= 5.5


@pytest.mark.django_db(transaction=True)
def test_bookmark_toggle_persists_after_reload(live_server, browser_page, browser_output_root):
    folder = browser_output_root["folder_name"]
    target_key = browser_output_root["segment_keys"][1]
    browser_page.goto(f"{live_server.url}/transcription/?folder={folder}", wait_until="domcontentloaded")

    selector = f"[data-bookmark-toggle][data-segment-key='{target_key}']"
    toggle = browser_page.locator(selector).first
    assert toggle.get_attribute("data-bookmarked") == "0"

    toggle.click()
    browser_page.wait_for_function(
        "sel => document.querySelector(sel)?.getAttribute('data-bookmarked') === '1'",
        selector,
    )

    browser_page.reload(wait_until="domcontentloaded")
    assert browser_page.locator(selector).first.get_attribute("data-bookmarked") == "1"


@pytest.mark.django_db(transaction=True)
def test_inline_segment_text_edit_persists_after_reload(live_server, browser_page, browser_output_root):
    folder = browser_output_root["folder_name"]
    new_text = "Texte modifie via browser"
    browser_page.goto(f"{live_server.url}/transcription/?folder={folder}", wait_until="domcontentloaded")

    editor_root = browser_page.locator("[title='Double-clic pour editer le texte']").first
    editor_root.locator(".cursor-text").first.dblclick()

    textarea = editor_root.locator("textarea")
    textarea.fill(new_text)
    textarea.press("Enter")

    browser_page.wait_for_function(
        "text => document.body.innerText.includes(text)",
        new_text,
    )
    browser_page.reload(wait_until="domcontentloaded")
    browser_page.wait_for_function(
        "text => document.body.innerText.includes(text)",
        new_text,
    )
