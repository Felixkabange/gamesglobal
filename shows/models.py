from django.db import models
from django.contrib.auth.models import User


class Show(models.Model):
    title = models.CharField(max_length=100)
    imdb_id = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    genre = models.CharField(max_length=50)
    icon = models.URLField()

    def __str__(self):
        return self.title


class Episode(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="episodes")
    season_number = models.IntegerField()
    episode_number = models.IntegerField()
    title = models.CharField(max_length=100)
    synopsis = models.TextField()

    def __str__(self):
        return (
            f"{self.title} - Season {self.season_number}, Episode {self.episode_number}"
        )


class WatchedEpisode(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="watched_episodes"
    )
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)
    watched_on = models.DateField()

    def __str__(self):
        return f"{self.user.username} watched {self.episode.title} on {self.watched_on}"
