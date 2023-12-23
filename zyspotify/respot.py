from io import BytesIO
from pathlib import Path
import json
import re
import requests
import time
from typing import List, Optional
from .db import db_manager
from .utils import FormatUtils
from .custom_types import *
import tempfile
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.core import ApiClient, Session
from librespot.metadata import TrackId, EpisodeId
from pydub import AudioSegment
from tqdm import tqdm
import logging

logger = logging.getLogger()


def removeDuplicates(lst):
    return [t for t in (set(tuple(i) for i in lst))]


MAX_AUTH_GET_RETRIES = 10
AUTH_GET_TIMEOUT = 10
AUTH_GET_RETRY_MULTIPLE_SEC = 10

API_ME = "https://api.spotify.com/v1/me/"


class Respot:
    def __init__(self, config_dir, force_premium, audio_format, antiban_wait_time):
        self.config_dir: Path = config_dir
        self.force_premium: bool = force_premium
        self.audio_format: str = audio_format
        self.antiban_wait_time: int = antiban_wait_time
        self.auth: RespotAuth = RespotAuth(self.force_premium)
        self.request: RespotRequest = None

    def is_authenticated(self, username=None, password=None) -> bool:
        if self.auth.login(username, password):
            self.request = RespotRequest(self.auth)
            return True
        return False

    def download(self, track_id, temp_path: Path, extension, make_dirs=True) -> str:
        handler = RespotTrackHandler(
            self.auth, self.audio_format, self.antiban_wait_time, self.auth.quality
        )
        if make_dirs:
            handler.create_out_dirs(temp_path.parent)

        # Download the audio
        filename = temp_path.stem
        audio_bytes = handler.download_audio(track_id, filename)

        if audio_bytes is None:
            return ""

        # Determine format of file downloaded
        audio_bytes_format = handler.determine_file_extension(audio_bytes)

        # Format handling
        output_path = temp_path

        if extension == audio_bytes_format:
            logging.info(f"Saving {output_path.stem} directly")
            handler.bytes_to_file(audio_bytes, output_path)
        elif extension == "source":
            output_str = filename + "." + audio_bytes_format
            output_path = temp_path.parent / output_str
            logging.info(f"Saving {filename} as {extension}")
            handler.bytes_to_file(audio_bytes, output_path)
        else:
            output_str = filename + "." + extension
            output_path = temp_path.parent / output_str
            logging.info(f"Converting {filename} to {extension}")
            handler.convert_audio_format(audio_bytes, output_path)

        return output_path


class RespotAuth:
    def __init__(self, force_premium):
        self.force_premium = force_premium
        self.session = None
        self.token = None
        self.token_your_library = None
        self.quality = None

    def login(self, username, password):
        """Authenticates with Spotify and saves credentials to the db"""

        if db_manager.has_stored_credentials():
            return self._authenticate_with_stored_credentials()
        elif username and password:
            return self._authenticate_with_user_pass(username, password)
        else:
            return False

    # librespot does not have a function to store credentials.json correctly
    def _persist_credentials(self) -> None:
        creds_file = Path("credentials.json")
        creds = json.loads(creds_file.read_text())
        db_manager.upsert_credentials(
            creds["username"], creds["credentials"], creds["type"], should_commit=True
        )
        creds_file.unlink(missing_ok=True)

    def _authenticate_with_stored_credentials(self):
        try:
            self.refresh_token()
            self._check_premium()
            return True
        except RuntimeError:
            return False

    def _authenticate_with_user_pass(self, username, password) -> bool:
        try:
            self.session = Session.Builder().user_pass(username, password).create()
            self._persist_credentials()
            self._check_premium()
            return True
        except RuntimeError:
            return False

    def refresh_token(self) -> (str, str):
        creds = db_manager.get_credentials()
        assert creds is not None

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            creds_json = {
                "username": creds[0],
                "credentials": creds[1],
                "type": creds[2],
            }

            json.dump(creds_json, tmp)
            tmp.flush()
            self.session = (
                Session.Builder().stored_file(stored_credentials=tmp.name).create()
            )
        # Remove auto generated credentials.json
        Path("credentials.json").unlink(missing_ok=True)
        self.token = self.session.tokens().get("user-read-email")
        self.token_your_library = self.session.tokens().get("user-library-read")
        return (self.token, self.token_your_library)

    def _check_premium(self) -> None:
        """If user has Spotify premium, return true"""
        if not self.session:
            raise RuntimeError("You must login first")

        account_type = self.session.get_user_attribute("type")
        if account_type == "premium" or self.force_premium:
            self.quality = AudioQuality.VERY_HIGH
            logging.info("[ DETECTED PREMIUM ACCOUNT - USING VERY_HIGH QUALITY ]\n")
        else:
            self.quality = AudioQuality.HIGH
            logging.info("[ DETECTED FREE ACCOUNT - USING HIGH QUALITY ]\n")

    def get_quality(self) -> AudioQuality:
        assert self.quality is not None
        return self.quality


class RespotRequest:
    def __init__(self, auth: RespotAuth):
        self.auth = auth
        self.token = auth.token
        self.token_your_library = auth.token_your_library

    def authorized_get_request(
        self, url: str, retry_count: int = 0, **kwargs
    ) -> Optional[requests.Response]:
        if retry_count > MAX_AUTH_GET_RETRIES:
            logger.critical(
                f"Max authorized_get_request retries ({MAX_AUTH_GET_RETRIES}) reached."
            )
            raise RuntimeError("Connection Error: Too many retries")

        def retry():
            time.sleep(retry_count * AUTH_GET_RETRY_MULTIPLE_SEC)
            return self.authorized_get_request(url, retry_count + 1, **kwargs)

        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {self.token_your_library if url.startswith(API_ME) else self.token}"
                },
                **kwargs,
                timeout=AUTH_GET_TIMEOUT,
            )

            response.raise_for_status()

            # if headers indicated response contained json, verify it decodes fine.
            if (
                response.status_code != 204 and
                response.headers["content-type"].strip().startswith("application/json")
            ):
                # a tad wasteful to not return the valid result, but what the callee does with the response is not always json
                response.json()


            # typical, errorless case
            return response

        except requests.exceptions.ConnectionError as e:
            logger.error(f"authorized_get_request ConnectionError: {'response had type none' if e.response is None else e.response.text}")
            retry()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.warning("Token expired, refreshing...")
                self.token, self.token_your_library = self.auth.refresh_token()
            else:
                logger.error(f"authorized_get_request HTTPError: {'response had type none' if e.response is None else e.response.text}")

            retry()

        except requests.exceptions.Timeout as e:
            logger.error(f"authorized_get_request Timeout: {'response had type none' if e.response is None else e.response.text}")
            retry()

        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"authorized_get_request JSONDecodeError: {'response had type none' if e.response is None else e.response.text}")
            retry()

        except requests.exceptions.RequestException as e:
            logger.error(f"authorized_get_request RequestException: {'response had type none' if e.response is None else e.response.text}")
            retry()

    def get_track_info(self, track_id) -> dict:
        """Retrieves metadata for downloaded songs"""
        try:
            info = json.loads(
                self.authorized_get_request(
                    "https://api.spotify.com/v1/tracks?ids="
                    + track_id
                    + "&market=from_token"
                ).text
            )

            # Sum the size of the images, compares and saves the index of the
            # largest image size
            sum_total = []
            for sum_px in info["tracks"][0]["album"]["images"]:
                sum_total.append(sum_px["height"] + sum_px["width"])

            img_index = sum_total.index(max(sum_total)) if sum_total else -1

            artist_id = info["tracks"][0]["artists"][0]["id"]

            artists = [data["name"] for data in info["tracks"][0]["artists"]]

            # TODO: Implement genre checking
            return {
                "id": track_id,
                "artist_id": artist_id,
                "artist_name": RespotUtils.conv_artist_format(artists),
                "album_artist": info["tracks"][0]["album"]["artists"][0]["name"],
                "album_name": info["tracks"][0]["album"]["name"],
                "audio_name": info["tracks"][0]["name"],
                "image_url": info["tracks"][0]["album"]["images"][img_index]["url"]
                if img_index >= 0
                else None,
                "release_year": info["tracks"][0]["album"]["release_date"].split("-")[
                    0
                ],
                "disc_number": info["tracks"][0]["disc_number"],
                "audio_number": info["tracks"][0]["track_number"],
                "scraped_song_id": info["tracks"][0]["id"],
                "is_playable": info["tracks"][0]["is_playable"],
                "release_date": info["tracks"][0]["album"]["release_date"],
            }

        except Exception as e:
            logging.critical("###   get_track_info - FAILED TO QUERY METADATA   ###")
            logging.critical("track_id:", track_id)
            logging.critical(e, exc_info=True)
            return None

    def get_all_user_playlists(self):
        """Returns list of users playlists"""
        playlists = []
        limit = 50
        offset = 0

        while True:
            resp = self.authorized_get_request(
                API_ME + "playlists",
                params={"limit": limit, "offset": offset},
            ).json()
            offset += limit
            playlists.extend(resp["items"])

            if len(resp["items"]) < limit:
                break

        return {"playlists": playlists}

    def get_playlist_songs(self, playlist_id):
        """returns list of songs in a playlist"""
        offset = 0
        limit = 100
        audios = []

        while True:
            resp = self.authorized_get_request(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                params={"limit": limit, "offset": offset},
            ).json()
            offset += limit
            for song in resp["items"]:
                if song["track"] is not None:
                    audios.append(
                        {
                            "id": song["track"]["id"],
                            "name": song["track"]["name"],
                            "artist": song["track"]["artists"][0]["name"],
                        }
                    )

            if len(resp["items"]) < limit:
                break
        return audios

    def get_playlist_info(self, playlist_id):
        """Returns information scraped from playlist"""
        resp = self.authorized_get_request(
            f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=name,owner(display_name)&market=from_token"
        ).json()
        return {
            "name": resp["name"].strip(),
            "owner": resp["owner"]["display_name"].strip(),
            "id": playlist_id,
        }

    def get_album_songs(
        self, album_id: SpotifyAlbumId, artist_id: SpotifyArtistId
    ) -> list[PackedSongs]:
        if not db_manager.have_all_album_songs(album_id):
            logging.info(f"need to request album {album_id}'s songs from spotify")
            songs = self.request_all_album_songs(album_id, artist_id)

            db_manager.store_album_songs(songs)

            db_manager.set_have_album_songs(album_id, True, should_commit=True)

        return db_manager.get_album_songs(album_id)

    def request_all_album_songs(
        self, album_id: SpotifyAlbumId, artist_id: SpotifyArtistId
    ) -> PackedSongs:
        """Returns album tracklist"""
        audios: PackedSongs = []
        offset = 0
        limit = 50
        include_groups = "album,compilation"

        # db only needs song_id, album_id, artist_id, name, quality
        quality = self.auth.get_quality()

        if quality == AudioQuality.HIGH:
            quality_kbps = 160
        elif quality == AudioQuality.VERY_HIGH:
            quality_kbps = 320
        else:
            quality_kbps = 0

        while True:
            resp = self.authorized_get_request(
                f"https://api.spotify.com/v1/albums/{album_id}/tracks",
                params={
                    "limit": limit,
                    "include_groups": include_groups,
                    "offset": offset,
                },
            ).json()
            offset += limit
            for song in resp["items"]:
                audios.append(
                    {
                        "id": song["id"],
                        "name": song["name"],
                        "track_number": song["track_number"],
                        "disc_number": song["disc_number"],
                        "quality_kbps": quality_kbps,
                        "album_id": album_id,
                        "artist_id": artist_id,
                    }
                )

            if len(resp["items"]) < limit:
                break

        return audios

    def get_album_info(self, album_id):
        """Returns album name"""
        resp = self.authorized_get_request(
            f"https://api.spotify.com/v1/albums/{album_id}"
        ).json()

        artists = []
        for artist in resp["artists"]:
            artists.append(FormatUtils.sanitize_data(artist["name"]))

        if match := re.search("(\\d{4})", resp["release_date"]):
            return {
                "artists": RespotUtils.conv_artist_format(artists),
                "name": resp["name"],
                "total_tracks": resp["total_tracks"],
                "release_date": match.group(1),
            }
        else:
            return {
                "artists": RespotUtils.conv_artist_format(artists),
                "name": resp["name"],
                "total_tracks": resp["total_tracks"],
                "release_date": resp["release_date"],
            }

    def get_artist_albums(self, artist_id) -> list[SpotifyAlbumId]:
        if not db_manager.have_all_artist_albums(artist_id):
            logging.info(f"need to request artist {artist_id}'s albums from spotify")
            all_artist_albums = self.request_all_artist_albums(artist_id)

            db_manager.store_all_artist_albums(artist_id, all_artist_albums)

            db_manager.set_have_all_artist_albums(artist_id, True, should_commit=True)

        # for consistency, always get result from db
        return db_manager.get_all_artist_albums(artist_id)

    def request_all_artist_albums(self, artist_id: SpotifyArtistId) -> PackedAlbums:
        """returns list of albums in an artist"""

        offset = 0
        limit = 50
        include_groups = "album,compilation,single"

        resp = self.authorized_get_request(
            f"https://api.spotify.com/v1/artists/{artist_id}/albums",
            params={"limit": limit, "include_groups": include_groups, "offset": offset},
        ).json()
        return resp["items"]

    def get_liked_tracks(self):
        """Returns user's saved tracks"""
        songs = []
        offset = 0
        limit = 50

        while True:
            resp = self.authorized_get_request(
                API_ME + "tracks",
                params={"limit": limit, "offset": offset},
            ).json()
            offset += limit
            for song in resp["items"]:
                songs.append(
                    {
                        "id": song["track"]["id"],
                        "name": song["track"]["name"],
                        "artist": song["track"]["artists"][0]["name"],
                    }
                )

            if len(resp["items"]) < limit:
                break

        return songs

    def get_episode_info(self, episode_id_str):
        info = json.loads(
            self.authorized_get_request(
                "https://api.spotify.com/v1/episodes/" + episode_id_str
            ).text
        )
        if not info:
            return None
        sum_total = []
        for sum_px in info["images"]:
            sum_total.append(sum_px["height"] + sum_px["width"])

        img_index = sum_total.index(max(sum_total)) if sum_total else -1

        return {
            "id": episode_id_str,
            "artist_id": info["show"]["id"],
            "artist_name": info["show"]["publisher"],
            "show_name": FormatUtils.sanitize_data(info["show"]["name"]),
            "audio_name": FormatUtils.sanitize_data(info["name"]),
            "image_url": info["images"][img_index]["url"] if img_index >= 0 else None,
            "release_year": info["release_date"].split("-")[0],
            "disc_number": None,
            "audio_number": None,
            "scraped_episode_id": ["id"],
            "is_playable": info["is_playable"],
            "release_date": info["release_date"],
        }

    def get_show_episodes(self, show_id):
        """returns episodes of a show"""
        episodes = []
        offset = 0
        limit = 50

        while True:
            resp = self.authorized_get_request(
                f"https://api.spotify.com/v1/shows/{show_id}/episodes",
                params={"limit": limit, "offset": offset},
            ).json()
            offset += limit
            for episode in resp["items"]:
                episodes.append(
                    {
                        "id": episode["id"],
                        "name": episode["name"],
                        "release_date": episode["release_date"],
                    }
                )

            if len(resp["items"]) < limit:
                break

        return episodes

    def get_show_info(self, show_id):
        """returns show info"""
        resp = self.authorized_get_request(
            f"https://api.spotify.com/v1/shows/{show_id}"
        ).json()
        return {
            "name": FormatUtils.sanitize_data(resp["name"]),
            "publisher": resp["publisher"],
            "id": resp["id"],
            "total_episodes": resp["total_episodes"],
        }

    def search(self, search_term, search_limit):
        """Searches Spotify's API for relevant data"""

        resp = self.authorized_get_request(
            "https://api.spotify.com/v1/search",
            params={
                "limit": search_limit,
                "offset": "0",
                "q": search_term,
                "type": "track,album,playlist,artist",
            },
        )

        ret_tracks = []
        tracks = resp.json()["tracks"]["items"]
        if len(tracks) > 0:
            for track in tracks:
                if track["explicit"]:
                    explicit = "[E]"
                else:
                    explicit = ""
                ret_tracks.append(
                    {
                        "id": track["id"],
                        "name": explicit + track["name"],
                        "artists": ",".join(
                            [artist["name"] for artist in track["artists"]]
                        ),
                    }
                )

        ret_albums = []
        albums = resp.json()["albums"]["items"]
        if len(albums) > 0:
            for album in albums:
                _year = re.search("(\\d{4})", album["release_date"]).group(1)
                ret_albums.append(
                    {
                        "name": album["name"],
                        "year": _year,
                        "artists": ",".join(
                            [artist["name"] for artist in album["artists"]]
                        ),
                        "total_tracks": album["total_tracks"],
                        "id": album["id"],
                    }
                )

        ret_playlists = []
        playlists = resp.json()["playlists"]["items"]
        for playlist in playlists:
            ret_playlists.append(
                {
                    "name": playlist["name"],
                    "owner": playlist["owner"]["display_name"],
                    "total_tracks": playlist["tracks"]["total"],
                    "id": playlist["id"],
                }
            )

        ret_artists = []
        artists = resp.json()["artists"]["items"]
        for artist in artists:
            ret_artists.append(
                {
                    "name": artist["name"],
                    "genres": "/".join(artist["genres"]),
                    "id": artist["id"],
                }
            )

        # TODO: Add search in episodes and shows

        if (
            len(ret_tracks) + len(ret_albums) + len(ret_playlists) + len(ret_artists)
            == 0
        ):
            return None
        else:
            return {
                "tracks": ret_tracks,
                "albums": ret_albums,
                "playlists": ret_playlists,
                "artists": ret_artists,
            }

    def get_all_liked_artists(self) -> List[SpotifyArtistId]:
        if not db_manager.have_all_liked_artists():
            logging.info("need to request liked artists from spotify")
            all_liked_spotify_artists = self.request_all_liked_artists()

            # store in db
            db_manager.store_all_liked_artists(all_liked_spotify_artists)

            db_manager.set_have_all_liked_artist(True, should_commit=True)

        # for consistency, always get result from db
        return db_manager.get_all_liked_artist_ids()

    def request_all_liked_artists(self) -> List[PackedArtists]:
        packed_artists: PackedArtists = []
        offset = 0
        limit = 50

        while True:
            resp = self.authorized_get_request(
                API_ME + "tracks",
                params={"limit": limit, "offset": offset},
            ).json()

            offset += limit
            try:
                for song in resp["items"]:
                    id = str(song["track"]["artists"][0]["id"])
                    name = str(song["track"]["artists"][0]["name"])
                    packed_artists.append((id, name))
            except KeyError:
                logging.error(
                    f"Failed to get liked artists for offset: {offset}, continuing"
                )
                continue
            if len(resp["items"]) < limit:
                break

        # insert all these artists into artist table
        # upsert all artists table so next time we dont have to call this

        return sorted(removeDuplicates(packed_artists))


class RespotTrackHandler:
    """Manages downloader and converter functions"""

    CHUNK_SIZE = 50000
    RETRY_DOWNLOAD = 30

    def __init__(self, auth, audio_format, antiban_wait_time, quality):
        """
        Args:
            audio_format (str): The desired format for the converted audio.
            quality (str): The quality setting of Spotify playback.
        """
        self.auth = auth
        self.format = audio_format
        self.antiban_wait_time = antiban_wait_time
        self.quality = quality

    def create_out_dirs(self, parent_path) -> None:
        parent_path.mkdir(parents=True, exist_ok=True)

    def download_audio(self, track_id, filename) -> BytesIO:
        """Downloads raw song audio from Spotify"""
        # TODO: ADD disc_number IF > 1

        try:
            try:
                _track_id = TrackId.from_base62(track_id)
                stream = self.auth.session.content_feeder().load(
                    _track_id, VorbisOnlyAudioQuality(self.quality), False, None
                )
            except ApiClient.StatusCodeException:
                _track_id = EpisodeId.from_base62(track_id)
                stream = self.auth.session.content_feeder().load(
                    _track_id, VorbisOnlyAudioQuality(self.quality), False, None
                )

            total_size = stream.input_stream.size
            downloaded = 0
            fail_count = 0
            audio_bytes = BytesIO()
            progress_bar = tqdm(total=total_size, unit="B", unit_scale=True)

            while downloaded < total_size:
                remaining = total_size - downloaded
                read_size = min(self.CHUNK_SIZE, remaining)
                data = stream.input_stream.stream().read(read_size)

                if not data:
                    fail_count += 1
                    if fail_count > self.RETRY_DOWNLOAD:
                        break
                else:
                    fail_count = 0  # reset fail_count on successful data read

                downloaded += len(data)
                progress_bar.update(len(data))
                audio_bytes.write(data)

            progress_bar.close()

            # Sleep to avoid ban
            time.sleep(self.antiban_wait_time)

            audio_bytes.seek(0)

            return audio_bytes

        except Exception as e:
            logging.critical("###   download_track - FAILED TO DOWNLOAD   ###")
            logging.critical(e, exc_info=True)
            logging.critical(track_id, filename)
            return None

    def convert_audio_format(self, audio_bytes: BytesIO, output_path: Path) -> None:
        """Converts raw audio (ogg vorbis) to user specified format"""
        # Make sure stream is at the start or else AudioSegment will act up
        audio_bytes.seek(0)

        bitrate = "160k"
        if self.quality == AudioQuality.VERY_HIGH:
            bitrate = "320k"

        AudioSegment.from_file(audio_bytes).export(
            output_path, format=self.format, bitrate=bitrate
        )

    def bytes_to_file(self, audio_bytes: BytesIO, output_path: Path) -> None:
        output_path.write_bytes(audio_bytes.getvalue())

    @staticmethod
    def determine_file_extension(audio_bytes: BytesIO) -> str:
        """Get MIME type from BytesIO object"""
        audio_bytes.seek(0)
        magic_bytes = audio_bytes.read(16)

        if magic_bytes.startswith(b"\xFF\xFB") or magic_bytes.startswith(b"\xFF\xFA"):
            return "mp3"
        elif b"RIFF" in magic_bytes and b"WAVE" in magic_bytes:
            return "wav"
        elif magic_bytes.startswith(b"fLaC"):
            return "flac"
        elif magic_bytes.startswith(b"OggS"):
            return "ogg"
        else:
            raise ValueError("The audio stream is malformed.")


class RespotUtils:
    @staticmethod
    def parse_url(search_input) -> dict:
        """Determines type of audio from url"""
        pattern = r"intl-[^/]+/"
        search_input = re.sub(pattern, "", search_input)

        track_uri_search = re.search(
            r"^spotify:track:(?P<TrackID>[0-9a-zA-Z]{22})$", search_input
        )
        track_url_search = re.search(
            r"^(https?://)?open\.spotify\.com/track/(?P<TrackID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            search_input,
        )

        album_uri_search = re.search(
            r"^spotify:album:(?P<AlbumID>[0-9a-zA-Z]{22})$", search_input
        )
        album_url_search = re.search(
            r"^(https?://)?open\.spotify\.com/album/(?P<AlbumID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            search_input,
        )

        playlist_uri_search = re.search(
            r"^spotify:playlist:(?P<PlaylistID>[0-9a-zA-Z]{22})$", search_input
        )
        playlist_url_search = re.search(
            r"^(https?://)?open\.spotify\.com/playlist/(?P<PlaylistID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            search_input,
        )

        episode_uri_search = re.search(
            r"^spotify:episode:(?P<EpisodeID>[0-9a-zA-Z]{22})$", search_input
        )
        episode_url_search = re.search(
            r"^(https?://)?open\.spotify\.com/episode/(?P<EpisodeID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            search_input,
        )

        show_uri_search = re.search(
            r"^spotify:show:(?P<ShowID>[0-9a-zA-Z]{22})$", search_input
        )
        show_url_search = re.search(
            r"^(https?://)?open\.spotify\.com/show/(?P<ShowID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            search_input,
        )

        artist_uri_search = re.search(
            r"^spotify:artist:(?P<ArtistID>[0-9a-zA-Z]{22})$", search_input
        )
        artist_url_search = re.search(
            r"^(https?://)?open\.spotify\.com/artist/(?P<ArtistID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
            search_input,
        )

        if track_uri_search is not None or track_url_search is not None:
            track_id_str = (
                track_uri_search if track_uri_search is not None else track_url_search
            ).group("TrackID")
        else:
            track_id_str = None

        if album_uri_search is not None or album_url_search is not None:
            album_id_str = (
                album_uri_search if album_uri_search is not None else album_url_search
            ).group("AlbumID")
        else:
            album_id_str = None

        if playlist_uri_search is not None or playlist_url_search is not None:
            playlist_id_str = (
                playlist_uri_search
                if playlist_uri_search is not None
                else playlist_url_search
            ).group("PlaylistID")
        else:
            playlist_id_str = None

        if episode_uri_search is not None or episode_url_search is not None:
            episode_id_str = (
                episode_uri_search
                if episode_uri_search is not None
                else episode_url_search
            ).group("EpisodeID")
        else:
            episode_id_str = None

        if show_uri_search is not None or show_url_search is not None:
            show_id_str = (
                show_uri_search if show_uri_search is not None else show_url_search
            ).group("ShowID")
        else:
            show_id_str = None

        if artist_uri_search is not None or artist_url_search is not None:
            artist_id_str = (
                artist_uri_search
                if artist_uri_search is not None
                else artist_url_search
            ).group("ArtistID")
        else:
            artist_id_str = None

        return {
            "track": track_id_str,
            "album": album_id_str,
            "playlist": playlist_id_str,
            "episode": episode_id_str,
            "show": show_id_str,
            "artist": artist_id_str,
        }

    @staticmethod
    def conv_artist_format(artists: list) -> str:
        """Returns string of artists separated by commas"""
        return ", ".join(artists)
