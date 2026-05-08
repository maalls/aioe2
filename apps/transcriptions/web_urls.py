from django.urls import path

from .views import (
    transcription_asset,
    transcription_bookmark_toggle,
    transcription_browser,
    transcription_edit_segment_text,
    transcription_edit_speaker_rename,
    transcription_edit_subtopic_rename,
    transcription_edit_topic_rename,
    transcription_preview,
)

urlpatterns = [
    path("", transcription_browser, name="transcription-browser"),
    path("preview/", transcription_preview, name="transcription-preview"),
    path("asset/<str:folder>/<str:filename>", transcription_asset, name="transcription-asset"),
    path("bookmark/<str:folder>/", transcription_bookmark_toggle, name="transcription-bookmark-toggle"),
    path(
        "edit/<str:folder>/segment/<str:segment_key>/text",
        transcription_edit_segment_text,
        name="transcription-edit-segment-text",
    ),
    path(
        "edit/<str:folder>/speaker/<str:speaker_id>/rename",
        transcription_edit_speaker_rename,
        name="transcription-edit-speaker-rename",
    ),
    path(
        "edit/<str:folder>/topic/<int:topic_id>/rename",
        transcription_edit_topic_rename,
        name="transcription-edit-topic-rename",
    ),
    path(
        "edit/<str:folder>/subtopic/<str:subtopic_id>/rename",
        transcription_edit_subtopic_rename,
        name="transcription-edit-subtopic-rename",
    ),
]
