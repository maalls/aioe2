from django.conf import settings
from django.db import models


class Project(models.Model):
	name = models.CharField(max_length=255)
	client = models.CharField(max_length=255, blank=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="projects",
	)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.name
