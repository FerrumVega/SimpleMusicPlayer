import yandex_music
import yandex_music.exceptions
import flask
import os
import config

client = yandex_music.Client(config.TOKEN).init()
app = flask.Flask(__name__)


def update_tracks_from_likes():
    tracks = client.tracks(track_info.id for track_info in client.users_likes_tracks())
    sorted_tracks = sorted(tracks, key=lambda t: (t.title.lower(), t.artists_name()))
    sorted_tracks_ids = [str(track_info.id) for track_info in sorted_tracks]
    return sorted_tracks, sorted_tracks_ids


def return_string_of_track_links(list_of_track_infos, from_query=False):
    list_of_links = (
        f"<a href='/track/{track_info.id}{"?from_query=true" if from_query else ""}'>{track_info.title} - {", ".join(track_info.artists_name())}</a>"
        for track_info in list_of_track_infos
    )
    string_of_links = "<br>".join(list_of_links)
    return string_of_links


@app.route("/search/")
def search():
    global sorted_tracks, sorted_tracks_ids
    search_results = client.search(
        flask.request.args.get("q"), type_="track"
    ).tracks.results
    sorted_tracks_ids = [str(track_info.id) for track_info in search_results]
    return flask.render_template(
        "search_results.html",
        search_results=return_string_of_track_links(
            search_results,
            True,
        ),
    )


@app.route("/")
def index():
    global sorted_tracks, sorted_tracks_ids
    sorted_tracks, sorted_tracks_ids = update_tracks_from_likes()
    return flask.render_template(
        "main_page.html", tracks_names=return_string_of_track_links(sorted_tracks)
    )


@app.route("/track/<track_id>/like")
def like_track(track_id):
    client.tracks(track_id)[0].like()
    return "", 204


@app.route("/track/<track_id>/dislike")
def dislike_track(track_id):
    client.tracks(track_id)[0].dislike()
    return "", 204


@app.route("/track/<track_id>/")
def track_page(track_id):
    global sorted_tracks, sorted_tracks_ids
    if flask.request.args.get("from_query", False) == False:
        sorted_tracks, sorted_tracks_ids = update_tracks_from_likes()
    track_info = client.tracks(track_id)[0]
    song_full_name = f"{track_info.title} - {", ".join(track_info.artists_name())}"
    song_path = f"static/{track_info.id}.mp3"
    cover_path = f"static/{track_info.id}.png"
    try:
        lyrics = track_info.get_lyrics().fetch_lyrics()
    except yandex_music.exceptions.NotFoundError:
        lyrics = "Нет текста песни"
    try:
        previous_track_url = (
            f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) - 1]}"
        )
    except ValueError:
        previous_track_url = ""
    try:
        next_track_url = (
            f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) + 1]}"
        )
    except ValueError:
        next_track_url = ""
    if not os.path.isfile(song_path):
        track_info.download(song_path)
    if not os.path.isfile(cover_path):
        track_info.download_cover(cover_path)
    return flask.render_template(
        "track_page.html",
        song_full_name=song_full_name,
        song_url=f"/{song_path}",
        previous_track_url=previous_track_url,
        next_track_url=next_track_url,
        song_lyrics=lyrics.replace("\n", "<br>"),
        song_cover=f"/{cover_path}",
    )


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT)
