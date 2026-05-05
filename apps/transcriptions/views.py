from rest_framework import generics

from .models import TranscriptionJob
from .serializers import TranscriptionJobCreateSerializer, TranscriptionJobDetailSerializer
from .tasks import run_transcription_task


class TranscriptionJobListCreateView(generics.ListCreateAPIView):
    queryset = TranscriptionJob.objects.select_related("project", "created_by").prefetch_related("result")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TranscriptionJobCreateSerializer
        return TranscriptionJobDetailSerializer

    def perform_create(self, serializer) -> None:
        user = self.request.user if self.request.user.is_authenticated else None
        job = serializer.save(created_by=user)
        run_transcription_task.delay(str(job.id))


class TranscriptionJobDetailView(generics.RetrieveAPIView):
    queryset = TranscriptionJob.objects.select_related("project", "created_by").prefetch_related("result")
    serializer_class = TranscriptionJobDetailSerializer
