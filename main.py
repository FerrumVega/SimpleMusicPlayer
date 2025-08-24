import yandex_music
import yandex_music.exceptions
import flask
import os
import config


def create_app():
    app = flask.Flask(__name__)

    def update_tracks_from_likes():
        tracks = client.tracks(
            track_info.id for track_info in client.users_likes_tracks()
        )
        sorted_tracks = sorted(
            tracks, key=lambda t: (t.title.lower(), t.artists_name())
        )
        sorted_tracks_ids = [str(track_info.id) for track_info in sorted_tracks]
        return sorted_tracks, sorted_tracks_ids

    def return_string_of_track_links(list_of_track_infos, from_query=False):
        list_of_links = (
            f"<a href='/track/{track_info.id}{"?from_query=true" if from_query else ""}'>{track_info.title} - {", ".join(track_info.artists_name())}{" [E]" if track_info.content_warning == "explicit" else ""}</a>"
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
            "main_page.html",
            tracks_names=return_string_of_track_links(
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

    @app.route("/track/<track_id>/like", methods=["POST"])
    def like_track(track_id):
        nonlocal liked_tracks
        liked_tracks = update_tracks_from_likes()[1]
        client.tracks(track_id)[0].like()
        return "", 204

    @app.route("/track/<track_id>/dislike", methods=["POST"])
    def dislike_track(track_id):
        nonlocal liked_tracks
        liked_tracks = update_tracks_from_likes()[1]
        client.tracks(track_id)[0].dislike()
        return "", 204

    @app.route("/feedback/<type>/", methods=["POST"])
    def feedback(type):
        global sorted_tracks_ids, wave_station
        player_pos = flask.request.args.get("player_pos", type=float)
        if player_pos == 0:
            player_pos = 0.1
        track_id = flask.request.args.get("track_id")
        if type == "ended":
            client.rotor_station_feedback_track_finished(
                station="user:onyourwave",
                track_id=track_id,
                total_played_seconds=player_pos,
                batch_id=wave_station.batch_id,
            )

        elif type == "skipped":
            client.rotor_station_feedback_skip(
                station="user:onyourwave",
                track_id=track_id,
                total_played_seconds=player_pos,
                batch_id=wave_station.batch_id,
            )
        return "", 204

    @app.route("/my_wave/")
    def wave():
        last_track_id = flask.request.args.get("last_track_id")
        global sorted_tracks_ids, wave_station
        wave_station = client.rotor_station_tracks(
            "user:onyourwave",
            settings2=True,
            **{"queue": last_track_id} if last_track_id is not None else {},
        )
        client.rotor_station_feedback_radio_started(
            station="user:onyourwave",
            from_=flask.request.user_agent,
            batch_id=wave_station.batch_id,
        )
        sorted_tracks = [full_info.track for full_info in wave_station.sequence]
        sorted_tracks_ids = [str(track_info.id) for track_info in sorted_tracks]
        return flask.redirect(f"/track/{sorted_tracks_ids[0]}?from_wave=true")

    @app.route("/track/<track_id>/")
    def track_page(track_id):
        global sorted_tracks, sorted_tracks_ids, wave_station
        nonlocal liked_tracks
        track_info = client.tracks(track_id)[0]
        song_full_name = f"{track_info.title} - {", ".join(track_info.artists_name())}{" [E]" if track_info.content_warning == "explicit" else ""}{" ❤️" if track_id in liked_tracks else ""}"
        song_path = f"static/tracks/{track_info.id}.mp3"
        cover_path = f"static/covers/{track_info.id}.png"
        os.makedirs(os.path.dirname(song_path), exist_ok=True)
        os.makedirs(os.path.dirname(cover_path), exist_ok=True)
        try:
            lyrics = track_info.get_lyrics().fetch_lyrics()
        except yandex_music.exceptions.NotFoundError:
            lyrics = "Нет текста песни"
        if (
            flask.request.args.get("from_query", "false") == "false"
            and flask.request.args.get("from_wave", "false") == "false"
        ):
            sorted_tracks, sorted_tracks_ids = update_tracks_from_likes()
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
        elif flask.request.args.get("from_query", "false") == "true":
            previous_track_url = ""
            try:
                next_track_url = f"/track/{client.tracks_similar(track_id).similar_tracks[1].id}?from_query=true"
            except IndexError:
                next_track_url = ""
        elif flask.request.args.get("from_wave", "false") == "true":
            client.rotor_station_feedback_track_started(
                station="user:onyourwave",
                track_id=track_id,
                batch_id=wave_station.batch_id,
            )
            previous_track_url = ""
            try:
                next_track_url = f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) + 1]}?from_wave=true"
            except IndexError:
                next_track_url = f"/my_wave?last_track_id={track_id}"
        if not os.path.isfile(song_path):
            track_info.download(song_path)
        if not os.path.isfile(cover_path):
            track_info.download_cover(cover_path, "1080x1080")
        return flask.render_template(
            "track_page.html",
            song_full_name=song_full_name,
            song_url=f"/{song_path}",
            previous_track_url=previous_track_url,
            next_track_url=next_track_url,
            song_lyrics=lyrics.replace("\n", "<br>"),
            song_cover=f"/{cover_path}",
        )

    liked_tracks = update_tracks_from_likes()[1]
    return app


if __name__ == "__main__":
    client = yandex_music.Client(config.TOKEN).init()
    app = create_app()
    app.run(host=config.HOST, port=config.PORT)
