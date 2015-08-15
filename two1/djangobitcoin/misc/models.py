from django.db import models

class BlackjackGame(models.Model):
     identifier = models.CharField(max_length=512, primary_key=True)
     blob = models.CharField(max_length=8096)
