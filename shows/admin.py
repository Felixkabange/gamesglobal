from django.contrib import admin
from .models import Show, Episode, WatchedEpisode

admin.site.register(Show)
admin.site.register(Episode)
admin.site.register(WatchedEpisode)
