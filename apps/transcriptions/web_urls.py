from django.urls import path

from .views import (
    transcription_asset,
    transcription_bookmark_toggle,
    transcription_browser,
    transcription_preview,
)

urlpatterns = [
    path("", transcription_browser, name="transcription-browser"),
    path("preview/", transcription_preview, name="transcription-preview"),
    path("asset/<str:folder>/<str:filename>", transcription_asset, name="transcription-asset"),
    path("bookmark/<str:folder>/", transcription_bookmark_toggle, name="transcription-bookmark-toggle"),
]
