from .conftest import render


def test_timeline_root_exposes_sync_and_bookmark_contract(folder_data):
    html = render(folder_data)

    assert 'id="timeline-sync-root"' in html
    assert 'data-sync-linked="1"' in html
    assert 'data-bookmark-url="' in html


def test_segment_row_exposes_time_window_contract(folder_data):
    html = render(folder_data)

    assert 'data-segment-item="1"' in html
    assert 'data-start="0' in html
    assert 'data-end="2' in html


def test_bookmark_toggle_exposes_segment_key_contract(folder_data):
    html = render(folder_data)

    assert 'data-bookmark-toggle' in html
    assert 'data-segment-key="abc123"' in html
    assert 'data-bookmarked="0"' in html


def test_required_script_modules_are_included(folder_data):
    html = render(folder_data)

    assert 'data-module="segments-table-interactions"' in html
    assert 'data-module="edit-inline-interactions"' in html
