from rest_framework import generics

from .models import Project
from .serializers import ProjectSerializer


class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.select_related("created_by")
    serializer_class = ProjectSerializer

    def perform_create(self, serializer) -> None:
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)
