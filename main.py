import yandex_music
import yandex_music.exceptions
import flask
import os
import config


def create_app():
    app = flask.Flask(__name__)

    @app.route("/favicon.ico")
    def favicon():
        return flask.send_from_directory(app.static_folder, "favicon.ico")

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

    @app.route("/track/<track_id>/<type>", methods=["POST"])
    def dislike_like_track(track_id, type):
        global liked_tracks_ids
        liked_tracks_ids = update_tracks_from_likes()[1]
        if type == "like":
            if track_id in liked_tracks_ids:
                if client.users_likes_tracks_remove(track_id):
                    return "Вы убрали лайк с трека", 200
                else:
                    return "Произошла ошибка", 500
            else:
                if client.tracks(track_id)[0].like():
                    return "Вы поставили лайк треку", 200
                else:
                    return "Произошла ошибка", 500
        elif type == "dislike":
            if client.tracks(track_id)[
                0
            ].dislike() and client.users_likes_tracks_remove(track_id):
                return 'Вы поставили "не нравится" треку'
            else:
                return "Произошла ошибка", 500
        liked_tracks_ids = update_tracks_from_likes()[1]

    @app.route("/feedback/<type>/", methods=["POST"])
    def feedback(type):
        global sorted_tracks_ids, wave_station
        player_pos = flask.request.args.get("player_pos", type=float)
        if player_pos == 0:
            player_pos = 0.1
        track_id = flask.request.args.get("track_id")
        wave_name = flask.request.args.get("wave_name")
        if type == "ended":
            client.rotor_station_feedback_track_finished(
                station=wave_name,
                track_id=track_id,
                total_played_seconds=player_pos,
            )

        elif type == "skipped":
            client.rotor_station_feedback_skip(
                station=wave_name,
                track_id=track_id,
                total_played_seconds=player_pos,
            )
        return "", 204

    @app.route("/my_wave/")
    def wave():
        global current_wave_track, sorted_tracks_ids, wave_station
        last_track_id = flask.request.args.get("last_track_id", "false")
        wave_name = flask.request.args.get("wave_name", "false")
        if wave_name == "user:onyourwave" and "current_wave_track" in globals():
            return flask.redirect(f"/track/{current_wave_track}?wave_name={wave_name}")
        wave_station = client.rotor_station_tracks(
            station=wave_name,
            **{"queue": last_track_id} if last_track_id != "false" else {},
        )
        client.rotor_station_feedback_radio_started(
            station=wave_name, from_=flask.request.user_agent
        )
        sorted_tracks = [full_info.track for full_info in wave_station.sequence]
        sorted_tracks_ids = [str(track_info.id) for track_info in sorted_tracks]
        return flask.redirect(f"/track/{sorted_tracks_ids[0]}?wave_name={wave_name}")

    @app.route("/track/<track_id>/")
    def track_page(track_id):
        global sorted_tracks, sorted_tracks_ids, wave_station, current_wave_track, liked_tracks_ids
        track_info = client.tracks(track_id)[0]
        liked_tracks_ids = update_tracks_from_likes()[1]
        song_full_name = f"{track_info.title} - {", ".join(track_info.artists_name())}{" [E]" if track_info.content_warning == "explicit" else ""}{" ❤️" if track_id in liked_tracks_ids else ""}"
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
            and flask.request.args.get("wave_name", "false") == "false"
        ):
            sorted_tracks, sorted_tracks_ids = update_tracks_from_likes()
            try:
                previous_track_url = (
                    f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) - 1]}"
                )
            except (ValueError, IndexError, NameError):
                previous_track_url = ""
            try:
                next_track_url = (
                    f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) + 1]}"
                )
            except (ValueError, IndexError, NameError):
                next_track_url = ""
        elif flask.request.args.get("from_query", "false") != "false":
            previous_track_url = ""
            try:
                next_track_url = f"/my_wave?wave_name=track:{track_id}"
            except (ValueError, IndexError, NameError):
                next_track_url = ""
        elif (wave_name := flask.request.args.get("wave_name", "false")) != "false":
            current_wave_track = track_id
            client.rotor_station_feedback_track_started(
                station=wave_name, track_id=track_id
            )
            try:
                previous_track_url = f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) - 1]}?wave_name={wave_name}"
            except (ValueError, IndexError, NameError):
                previous_track_url = ""
            try:
                next_track_url = f"/track/{sorted_tracks_ids[sorted_tracks_ids.index(track_id) + 1]}?wave_name={wave_name}"
            except (ValueError, IndexError, NameError):
                next_track_url = (
                    f"/my_wave?last_track_id={track_id}&wave_name={wave_name}"
                )
        if not os.path.isfile(song_path):
            track_info.download(song_path)
        if not os.path.isfile(cover_path):
            track_info.download_cover(cover_path, "1080x1080")
        return flask.render_template(
            "track_page.html",
            song_full_name=song_full_name,
            song_title=track_info.title,
            song_artists=", ".join(track_info.artists_name()),
            song_url=f"/{song_path}",
            previous_track_url=previous_track_url,
            next_track_url=next_track_url,
            song_lyrics=lyrics.replace("\n", "<br>"),
            song_cover=f"/{cover_path}",
        )

    liked_tracks_ids = update_tracks_from_likes()[1]
    return app


if __name__ == "__main__":
    client = yandex_music.Client(config.TOKEN).init()
    app = create_app()
    app.run(host=config.HOST, port=config.PORT)
