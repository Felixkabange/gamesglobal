from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("shows/", views.show_list, name="shows"),
    path("logout/", views.logout_view, name="logout"),
    path("search/", views.search_shows, name="search"),
    path("add/", views.add_show, name="add"),
    path("show/<int:show_id>/", views.show_details, name="show_details"),
    path("remove/<int:show_id>/", views.remove_show, name="remove"),
    path("watched/<int:episode_id>/",views.mark_episode_watched,name="mark_episode_watched"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
