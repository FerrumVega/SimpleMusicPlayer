from yandex_music import Client
from flask import Flask, send_file
import io
import config

client = Client(config.TOKEN).init()
tracks = client.tracks([track_info.id for track_info in client.users_likes_tracks()])
app = Flask(__name__)


@app.route("/tracks/")
def index():
    links = [
        f'<a href="/track/{track.id}">{track.title} - {", ".join([artist.name for artist in track.artists])}</a>'
        for track in tracks
    ]
    return "<br>".join(links)


@app.route("/track/<track_id>/")
def t(track_id):
    track_bytes = client.tracks(track_id)[0].download_bytes()
    return send_file(
        io.BytesIO(track_bytes), mimetype="audio/mpeg", as_attachment=False
    )


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT)
