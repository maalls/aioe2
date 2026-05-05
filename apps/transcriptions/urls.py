from django.urls import path

from .views import TranscriptionJobDetailView, TranscriptionJobListCreateView

urlpatterns = [
	path("", TranscriptionJobListCreateView.as_view(), name="transcription-job-list"),
	path("<uuid:pk>/", TranscriptionJobDetailView.as_view(), name="transcription-job-detail"),
]
