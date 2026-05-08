from .conftest import render


def test_render_does_not_include_legacy_fallback_table(folder_data):
    html = render(folder_data)

    assert "min-w-full divide-y divide-slate-200" not in html
    assert "Aucun segment trouve." not in html
    assert "Aucun groupe timeline disponible." not in html
