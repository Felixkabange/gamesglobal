from django.shortcuts import render, redirect
from django.contrib.auth.models import User
import json
from django.db import IntegrityError
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Show, WatchedEpisode, Episode
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
import urllib.parse
import requests


def index(request):
    return render(request, "shows/index.html")


def login_view(request):  # Renamed to avoid conflict with 'login' from Django
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(
            request, username=username, password=password
        )  # Renamed variable

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))  # Redirects to the index view
        else:
            # Using messages to add error message
            messages.error(request, "Invalid username and/or password")
            return redirect(
                "login"
            )  # Redirect back to login page to show the error message
    else:
        return render(request, "shows/login.html")


def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirmation = request.POST.get("confirmation")

        # Ensure all fields are filled
        if not all([username, email, password, confirmation]):
            messages.error(request, "Please fill in all fields.")
            return redirect("signup")

        # Ensure password matches confirmation
        if password != confirmation:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        # Try to create a new user
        try:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Account created successfully. Please log in.")
            return redirect("login")
        except IntegrityError:
            messages.error(request, "Username already taken.")
            return redirect("signup")
    else:
        return render(request, "shows/signup.html")


def logout_view(request):
    if not request.user.is_authenticated:
        message = "You need to register first."
        redirect_url = reverse("register")
        return render(request, {"message": message, "redirect_url": redirect_url})

    logout(request)
    return HttpResponseRedirect(reverse("index"))


def show_list(request):
    if not request.user.is_authenticated:
        return redirect("login")

    shows = Show.objects.all()
    watched_episodes = WatchedEpisode.objects.filter(user=request.user)
    next_episodes = {}

    for show in shows:
        episodes = Episode.objects.filter(show=show).order_by(
            "season_number", "episode_number"
        )
        watched_show_episodes = watched_episodes.filter(episode__in=episodes)

        if watched_show_episodes.count() == episodes.count():
            next_episodes[show.id] = None  # All episodes watched
        else:
            for episode in episodes:
                if not watched_show_episodes.filter(episode=episode).exists():
                    next_episodes[show.id] = episode
                    break

    context = {
        "shows": shows,
        "watched_shows": {we.episode.show.id for we in watched_episodes},
        "next_episodes": next_episodes,
    }
    return render(request, "shows/show_list.html", context)


def add_show(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()  # Get title and remove any leading/trailing whitespace
        if title:
            title_normalized = title.lower()  # Convert title to lowercase
            show = add_show_from_api(title_normalized)  # Use the normalized title for API call or database query
            if show:  # Check if show was successfully added
                return redirect("show_details", show_id=show.id)
            else:
                # Optionally, handle cases where the show couldn't be added
                return render(request, "shows/add_show_form.html", {
                    "error": "Show could not be added. Please check the title and try again."
                })
    return render(request, "shows/add_show_form.html")


def show_details(request, show_id):
    show = get_object_or_404(Show, id=show_id)
    episodes = Episode.objects.filter(show=show).order_by(
        "season_number", "episode_number"
    )
    watched_ids = set(
        WatchedEpisode.objects.filter(
            user=request.user, episode__in=episodes
        ).values_list("episode_id", flat=True)
    )

    episodes_data = [
        {
            "id": episode.id,
            "title": episode.title,
            "season_number": episode.season_number,
            "episode_number": episode.episode_number,
            "watched": episode.id in watched_ids,
        }
        for episode in episodes
    ]

    context = {
        "show": show,
        "episodes": episodes_data,
    }
    return render(request, "shows/show_details.html", context)


def remove_show(request, show_id):
    if request.method == "POST":
        Show.objects.filter(id=show_id).delete()
        return redirect("shows")
    else:
        # Redirect to the shows list or some other page if not POST
        return redirect("shows")


@login_required
@csrf_exempt  # Only if you're unable to set CSRF token correctly
def mark_episode_watched(request, episode_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        episode = get_object_or_404(Episode, id=episode_id)
        WatchedEpisode.objects.get_or_create(user=request.user, episode=episode, defaults={'watched_on': timezone.now()})
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


# The view in Charge of Making the API request to IMBD
def get_show_data(title):
    api_key = "2a792897"
    title_encoded = urllib.parse.quote(title)
    url = f"https://www.omdbapi.com/?t={title_encoded}&type=series&plot=full&apikey={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to fetch data: {e}")
        return {}


def add_show_from_api(title):
    show_data = get_show_data(title)
    if show_data:
        # Create and save show instance
        show, created = Show.objects.get_or_create(
            imdb_id=show_data.get("imdbID"),
            defaults={
                "title": show_data.get("Title"),
                "description": show_data.get("Plot"),
                "genre": show_data.get("Genre"),
                "icon": show_data.get("Poster"),
            },
        )
        if created:
            print(f"Added new show: {show.title}")
        else:
            print(f"Show already exists: {show.title}")
        return show
    else:
        print("No data found for this title")
        return None


def add_episodes_to_show(show, season_data):
    for episode_data in season_data.get("Episodes", []):
        Episode.objects.get_or_create(
            show=show,
            season_number=season_data.get(
                "Season", 1
            ),  # Default season to 1 if not specified
            episode_number=episode_data.get("Episode"),
            defaults={
                "title": episode_data.get("Title"),
                "synopsis": episode_data.get(
                    "Plot", "No synopsis available"
                ),  # Provide a default if Plot is missing
            },
        )


def get_season_data(imdb_id, season):
    api_key = "2a792897"
    url = f"https://www.omdbapi.com/?i={imdb_id}&Season={season}&apikey={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to fetch data for season {season}: {e}")
        return {}


# For the search functionality in my layout.html
def search_shows(request):
    query = request.GET.get("query", "")
    shows = Show.objects.filter(
        title__icontains=query
    )  # Case-insensitive containment search
    return render(request, "shows/search_results.html", {"shows": shows})
