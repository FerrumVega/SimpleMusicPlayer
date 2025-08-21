from yandex_music import Client
import flask
import os
import config

client = Client(config.TOKEN).init()
tracks = client.tracks(track_info.id for track_info in client.users_likes_tracks())
sorted_tracks = sorted(tracks, key=lambda t: (t.title.lower(), t.artists_name()))
sorted_tracks_ids = [track_info.id for track_info in sorted_tracks]
app = flask.Flask(__name__)


@app.route("/")
def index():
    links = (
        f'<a href="/track/{track_info.id}">{track_info.title} - {", ".join(track_info.artists_name())}</a>'
        for track_info in sorted_tracks
    )
    return "<br>".join(links)


@app.route("/track/<track_id>/")
def track_page(track_id):
    track_info = client.tracks(track_id)[0]
    song_full_name = f"{track_info.title} - {", ".join(track_info.artists_name())}"
    song_path = f"static/{track_info.id}.mp3"
    if not os.path.isfile(song_path):
        track_info.download(song_path)
    return flask.render_template(
        "track_page.html",
        song_full_name=song_full_name,
        song_url=f"/{song_path}",
        previous_track_url=f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) - 1]}",
        next_track_url=f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) + 1]}",
    )


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT)
