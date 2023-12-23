import sys
import time
from requests import get
from getpass import getpass
from pathlib import Path
import importlib.metadata as metadata
import os
from .custom_types import *
from .db import db_manager
from .respot import Respot, RespotUtils
from .tagger import AudioTagger
from .utils import FormatUtils
from .arg_parser import parse_args
import logging
from logging.handlers import RotatingFileHandler
from logging.config import dictConfig

try:
    __version__ = metadata.version("zyspotify")
except metadata.PackageNotFoundError:
    __version__ = "unknown"

_USERNAME = os.environ.get("USERNAME", None)
_PASSWORD = os.environ.get("PASSWORD", None)

# using __name__ instead of the root logger seems to be the "proper" way, but:
# librespot logs crap to INFO that we don't care about
# same logger config's would need to be done in each module, which is nasty
logger = logging.getLogger()

class ZYSpotify:
    def __init__(self):
        self.SEPARATORS = [",", ";"]
        self.args = parse_args()
        self.respot = Respot(
            config_dir=self.args.config_dir,
            force_premium=self.args.force_premium,
            audio_format=self.args.audio_format,
            antiban_wait_time=self.args.antiban_time,
        )
        self.search_limit = self.args.limit

        # User defined directories
        self.config_dir = Path(self.args.config_dir)
        self.download_dir = Path(self.args.download_dir)
        self.music_dir = Path(self.args.music_dir)
        self.episodes_dir = Path(self.args.episodes_dir)

        self.album_in_filename = self.args.album_in_filename
        self.antiban_album_time = self.args.antiban_album
        self.not_skip_existing = self.args.not_skip_existing
        self.tagger = AudioTagger()

        self.log_dir_path = Path(self.args.log_dir)
        self.log_dir_path.mkdir(exist_ok=True)


        """
        TLDR: log level WARNING and up to a file by default, and to stdout level INFO and up by default
        """

        # should remain root logger, ideally actual logger entries use "__name__"
        logger = logging.getLogger("root")

        # remove librespot info logging junk
        dictConfig({"version": 1, "disable_existing_loggers":True})

        log_file_handler = RotatingFileHandler((self.log_dir_path / "zyspotify.log"), maxBytes=int(self.args.max_log_size_bytes))
        log_file_handler.setFormatter(logging.Formatter("%(levelname)s - [%(asctime)s] - {%(filename)s:%(funcName)s:%(lineno)d}: %(message)s", "%Y-%m-%dT%H:%M:%S%z"))
        log_file_handler.setLevel(self.args.log_file_level)
        logger.addHandler(log_file_handler)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        stdout_handler.setLevel(self.args.stdout_log_level)
        logger.addHandler(stdout_handler)

        logger.setLevel(logging.DEBUG) # NEEDS TO BE SET TO MINIMUM LOG LEVEL EXPECTED FOR ANY HANDLER
        logging.debug("Logging Initalized")

    def splash(self):
        """Displays splash screen"""
        print(FormatUtils.GREEN)
        print(
            """
    ███████     ███████ ██████   ██████  ████████ ██ ███████ ██    ██
       ███      ██      ██   ██ ██    ██    ██    ██ ██       ██  ██
      ███   y   ███████ ██████  ██    ██    ██    ██ █████     ████
     ███             ██ ██      ██    ██    ██    ██ ██         ██
    ███████     ███████ ██       ██████     ██    ██ ██         ██
        """
        )
        print(FormatUtils.RESET)
        logger.info(f"version: {__version__}")

    def split_input(self, selection):
        """Splits the input into a list"""
        # if one from separator in selections
        for sep in self.SEPARATORS:
            if sep in selection:
                return selection.split(sep)
        return [selection]

    @staticmethod
    def clear():
        """Clear the console window"""
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")

    @staticmethod
    def antiban_wait(seconds=5):
        """Pause between albums for a set number of seconds"""
        for i in range(seconds)[::-1]:
            print(f"\rSleep for {i + 1} second(s)...", end="")
            time.sleep(1)
        print("\n")

    @staticmethod
    def zfill(value, length=2):
        """Returns fill the strings with zeros"""
        return str(value).zfill(length)

    def login(self):
        """Login to Spotify"""
        while not self.respot.is_authenticated():
            if _USERNAME is not None and _PASSWORD is not None:
                username = _USERNAME
                password = _PASSWORD
            else:
                logging.info("Login to Spotify")
                username = input("Username: ")
                password = getpass("Password: ")
            if self.respot.is_authenticated(username, password):
                return True
        return True

    @staticmethod
    def shorten_filename(filename, artist_name, audio_name, max_length=75):
        if len(filename) > max_length and len(artist_name) > (max_length // 2):
            filename = filename.replace(artist_name, "Various Artists")
        else:
            truncated_audio_name = audio_name[:max_length]
            filename = filename.replace(audio_name, truncated_audio_name)

        return filename

    def generate_filename(
        self,
        caller,
        audio_name,
        audio_number,
        artist_name,
        album_name,
    ):
        if caller == "album":
            filename = f"{audio_number}. {audio_name}"

            if self.album_in_filename:
                filename = f"{album_name} " + filename

        elif caller == "playlist":
            filename = f"{audio_name}"

            if self.album_in_filename:
                filename = f"{album_name} - " + filename
            filename = f"{artist_name} - " + filename

        elif caller == "show":
            filename = f"{audio_number}. {audio_name}"

        elif caller == "episode":
            filename = f"{artist_name} - {audio_number}. {audio_name}"

        else:
            filename = f"{artist_name} - {audio_name}"

        filename = self.shorten_filename(filename, artist_name, audio_name)
        filename = FormatUtils.sanitize_data(filename)

        return filename

    def download_track(self, track_id, path=None, caller=None):
        if not db_manager.have_song_downloaded(track_id):
            if caller == "show" or caller == "episode":
                track = self.respot.request.get_episode_info(track_id)
            else:
                track = self.respot.request.get_track_info(track_id)

            if track is None:
                logging.error(f"Skipping {track_id} - Could not get track info")
                return True

            if not track["is_playable"]:
                logging.error(f"Skipping {track['audio_name']} - Not Available")
                return True

            audio_name = track.get("audio_name")
            audio_number = track.get("audio_number")
            artist_name = track.get("artist_name")
            album_artist = track.get("album_artist")
            album_name = track.get("album_name")

            filename = self.generate_filename(
                caller,
                audio_name,
                audio_number,
                artist_name,
                album_name,
            )

            base_path = path or self.music_dir
            if caller == "show" or caller == "episode":
                base_path = path or self.episodes_dir
            temp_path = base_path / (filename + "." + self.args.audio_format)

            for ext in (".mp3", ".ogg"):
                if (
                    self.not_skip_existing
                    and (song_path := (base_path / (filename + ext))).exists()
                ):
                    db_manager.set_song_downloaded(
                        track_id, Path(song_path), should_commit=True
                    )
                    logging.warning(f"Skipping {filename + ext} - Already downloaded")
                    return True

            output_path = self.respot.download(
                track_id, temp_path, self.args.audio_format, True
            )

            if output_path == "":
                return

            logging.info(f"Setting audiotags {filename}")
            self.tagger.set_audio_tags(
                output_path,
                artists=artist_name,
                name=audio_name,
                album_name=album_name,
                release_year=track["release_year"],
                disc_number=track["disc_number"],
                track_number=audio_number,
                album_artist=album_artist,
                track_id_str=track["scraped_song_id"],
                image_url=track["image_url"],
            )

            db_manager.set_song_downloaded(
                track_id, Path(output_path), should_commit=True
            )
            logging.info(f"Finished downloading {filename}")

        else:
            logging.warning(f"Skipping song {track_id}, already downloaded")

    def download_playlist(self, playlist_id):
        playlist = self.respot.request.get_playlist_info(playlist_id)
        if not playlist:
            logging.error("Playlist not found")
            return False
        songs = self.respot.request.get_playlist_songs(playlist_id)
        if not songs:
            logging.error("Playlist is empty")
            return False
        playlist_name = playlist["name"]
        if playlist_name == "":
            playlist_name = playlist_id
        logging.info(f"Downloading {playlist_name} playlist")
        basepath = self.music_dir / FormatUtils.sanitize_data(playlist_name)
        for song in songs:
            self.download_track(song["id"], basepath, "playlist")
        logging.info(f"Finished downloading {playlist['name']} playlist")

    def download_all_user_playlists(self):
        playlists = self.respot.request.get_all_user_playlists()
        if not playlists:
            logging.error("No playlists found")
            return False
        for playlist in playlists["playlists"]:
            self.download_playlist(playlist["id"])
            self.antiban_wait(self.antiban_album_time)
        logging.info("Finished downloading all user playlists")

    def download_select_user_playlists(self):
        playlists = self.respot.request.get_all_user_playlists()
        if not playlists:
            logging.error("No playlists found")
            return False
        for i, playlist in enumerate(playlists["playlists"]):
            logging.info(f"    {i + 1}. {playlist['name']}")

        logging.info(
            """
        > SELECT A PLAYLIST BY ID.
        > SELECT A RANGE BY ADDING A DASH BETWEEN BOTH ID's.
          For example, typing 10 to get one playlist or 10-20 to get
          every playlist from 10-20 (inclusive).
        > SELECT A MULTIPLE PLAYLISTS BY ADDING A COMMA BETWEEN IDs.
          For example, typing 10,11,20 will select playlists
          10, 11 and 20 respectively.
          Typing 1,11-20 will select playlists 1 and 11-20 (inclusive).
        """
        )
        user_input = input("ID(s): ")

        # Parse user input
        user_formatted_input = set()
        for part in user_input.split(","):
            x = part.split("-")
            user_formatted_input.update(range(int(x[0]), int(x[-1]) + 1))
        sorted(user_formatted_input)

        # Clean user input
        invalid_ids = []
        playlist_ids = []
        for track_id in user_formatted_input:
            if track_id > len(playlists["playlists"]) or track_id < 1:
                invalid_ids.append(track_id)
            else:
                playlist_ids.append(playlists["playlists"][track_id - 1]["id"])
        if invalid_ids:
            logging.warning(f"{invalid_ids} do not exist, downloading the rest")

        for playlist in playlist_ids:
            self.download_playlist(playlist)
            self.antiban_wait(self.antiban_album_time)
        logging.info("Finished downloading selected playlists")

    def download_album(
        self, album_id: SpotifyAlbumId, artist_id: SpotifyArtistId
    ) -> bool:
        if not db_manager.have_album_already_downloaded(album_id):
            album = self.respot.request.get_album_info(album_id)
            if not album:
                logging.error("Album not found")
                return False

            songs = self.respot.request.get_album_songs(album_id, artist_id)

            if not songs:
                logging.error("Album is empty")
                return False
            disc_number_flag = False
            for song in songs:
                if song["disc_number"] > 1:
                    disc_number_flag = True

            # Sanitize beforehand
            artists = FormatUtils.sanitize_data(album["artists"])
            album_name = FormatUtils.sanitize_data(
                f"{album['release_date']} - {album['name']}"
            )

            logging.info(f"Downloading {artists} - {album_name} album")

            # Concat download path
            basepath = self.music_dir / artists / album_name

            self.respot
            for song in songs:
                # if song already downloaded, skip

                # Append disc number to filepath if more than 1 disc
                newBasePath = basepath
                if disc_number_flag:
                    disc_number = FormatUtils.sanitize_data(
                        f"{self.zfill(song['disc_number'])}"
                    )
                    newBasePath = basepath / disc_number

                self.download_track(song["id"], newBasePath, "album")

            db_manager.set_album_fully_downloaded(album_id, should_commit=True)
            logging.info(f"Finished downloading {album['artists']} - {album['name']} album")
        else:
            logging.warning(f"Skipping album {album_id}, already fully downloaded")
            return False
        return True

    def download_artist(self, artist_id: SpotifyArtistId):
        if not db_manager.have_artist_already_downloaded(artist_id):
            albums_ids = self.respot.request.get_artist_albums(artist_id)
            if not albums_ids:
                logging.error(f"Artist {artist_id} has no albums")
                return False
            for album_id in albums_ids:
                # only preform antiban wait if we actually downloaded something
                if self.download_album(album_id, artist_id):
                    self.antiban_wait(self.antiban_album_time)

            db_manager.set_artist_fully_downloaded(artist_id, should_commit=True)
            logging.info(f"Finished downloading {artist_id} artist")
        else:
            logging.warning(f"Skipping artist {artist_id}, already fully downloaded")
        return True

    def download_all_songs_from_all_liked_artists(self):
        artist_ids = self.respot.request.get_all_liked_artists()
        logging.info(f"Downloading [{len(artist_ids)}] artists")

        for artist_id in artist_ids:
            self.download_artist(artist_id)

    def download_liked_songs(self):
        songs = self.respot.request.get_liked_tracks()
        if not songs:
            logging.error("No liked songs found")
            return False
        logging.info("Downloading liked songs")
        basepath = self.music_dir / "Liked Songs"
        for song in songs:
            self.download_track(song["id"], basepath, "liked_songs")
        logging.info("Finished downloading liked songs")
        return True

    def download_by_url(self, url):
        parsed_url = RespotUtils.parse_url(url)
        if parsed_url["track"]:
            ret = self.download_track(parsed_url["track"])
        elif parsed_url["playlist"]:
            ret = self.download_playlist(parsed_url["playlist"])
        elif parsed_url["album"]:
            ret = self.download_album(parsed_url["album"])
        elif parsed_url["artist"]:
            ret = self.download_artist(parsed_url["artist"])
        elif parsed_url["episode"]:
            ret = self.download_track(parsed_url["episode"])
        elif parsed_url["show"]:
            ret = self.download_all_show_episodes(parsed_url["show"])
        else:
            logging.error("Invalid URL")
            return False
        return ret

    def download_all_show_episodes(self, show_id):
        show = self.respot.request.get_show_info(show_id)
        if not show:
            logging.error("Show not found")
            return False
        episodes = self.respot.request.get_show_episodes(show_id)
        if not episodes:
            logging.error("Show has no episodes")
            return False
        for episode in episodes:
            self.download_track(episode["id"], "show")
        logging.info(f"Finished downloading {show['name']} show")
        return True

    def search(self, query):
        if "https" in query:
            self.download_by_url(query)
            return True

        # TODO: Add search by artist, album, playlist, etc.
        results = self.respot.request.search(query, self.search_limit)
        if not results:
            logging.warning("No results found")
            return False
        logging.info("Search results:")
        logging.info(f"{FormatUtils.GREEN}TRACKS{FormatUtils.RESET}")
        full_results = []
        i = 1
        for result in results["tracks"]:
            logging.info(f"{i}. {result['artists']} - {result['name']}")
            result["type"] = "track"
            full_results.append(result)
            i += 1
        logging.info(f"\n{FormatUtils.GREEN}ALBUMS{FormatUtils.RESET}")
        for result in results["albums"]:
            logging.info(f"{i}. {result['artists']} - {result['name']}")
            result["type"] = "album"
            full_results.append(result)
            i += 1
        logging.info(f"\n{FormatUtils.GREEN}PLAYLISTS{FormatUtils.RESET}")
        for result in results["playlists"]:
            logging.info(f"{i}. {result['name']}")
            result["type"] = "playlist"
            full_results.append(result)
            i += 1
        logging.info(f"\n{FormatUtils.GREEN}ARTISTS{FormatUtils.RESET}")
        for result in results["artists"]:
            logging.info(f"{i}. {result['name']}")
            result["type"] = "artist"
            full_results.append(result)
            i += 1
        logging.info("")
        logging.info("Enter the number of the item you want to download")
        logging.info(f"allowed delimiters: {self.SEPARATORS}")
        logging.info("Enter 'all' to download all items")
        logging.info("Enter 'exit' to exit")
        selection = input(">>>")
        while selection == "":
            selection = input(">>>")
        if selection == "exit":
            return False
        if selection == "all":
            for result in full_results:
                if result["type"] == "track":
                    self.download_track(result["id"])
                elif result["type"] == "album":
                    self.download_album(result["id"])
                elif result["type"] == "playlist":
                    self.download_playlist(result["id"])
                elif result["type"] == "artist":
                    self.download_artist(result["id"])
            return True
        for item in self.split_input(selection):
            if int(item) >= len(full_results) + 1:
                logging.error("Invalid selection")
                return False
            result = full_results[int(item) - 1]
            if result["type"] == "track":
                self.download_track(result["id"])
            elif result["type"] == "album":
                self.download_album(result["id"])
            elif result["type"] == "playlist":
                self.download_playlist(result["id"])
            elif result["type"] == "artist":
                self.download_artist(result["id"])
        return True

    def start(self):
        """Main client loop"""
        if self.args.version:
            logging.info(f"ZYSpotify {__version__}")
            return

        logger.debug(f"Public IP: {get('https://api.ipify.org').content.decode('utf8')}")

        self.splash()
        while not self.login():
            logging.error("Invalid credentials")

        if self.args.all_playlists:
            raise NotImplementedError()
            self.download_all_user_playlists()
        elif self.args.select_playlists:
            raise NotImplementedError()
            self.download_select_user_playlists()
        elif self.args.liked_songs:
            raise NotImplementedError()
            self.download_liked_songs()
        elif self.args.all_liked_all_artists:
            self.download_all_songs_from_all_liked_artists()
        elif self.args.playlist:
            raise NotImplementedError()
            for playlist in self.split_input(self.args.playlist):
                if "spotify.com" in self.args.playlist:
                    self.download_by_url(playlist)
                else:
                    self.download_playlist(playlist)
        elif self.args.album:
            raise NotImplementedError()
            for album in self.split_input(self.args.album):
                if "spotify.com" in self.args.album:
                    self.download_by_url(album)
                else:
                    self.download_album(album)
        elif self.args.artist:
            for artist in self.split_input(self.args.artist):
                if "spotify.com" in self.args.artist:
                    self.download_by_url(artist)
                else:
                    self.download_artist(artist)
        elif self.args.track:
            raise NotImplementedError()
            for track in self.split_input(self.args.track):
                if "spotify.com" in self.args.track:
                    self.download_by_url(track)
                else:
                    self.download_track(track)
            logging.info("All Done")
        elif self.args.episode:
            raise NotImplementedError()
            for episode in self.split_input(self.args.episode):
                if "spotify.com" in self.args.episode:
                    self.download_by_url(episode)
                else:
                    self.download_track(episode)
        elif self.args.full_show:
            raise NotImplementedError()
            for show in self.split_input(self.args.full_show):
                if "spotify.com" in self.args.full_show:
                    self.download_by_url(show)
                else:
                    self.download_all_show_episodes(show)
        elif self.args.search:
            raise NotImplementedError()
            for query in self.split_input(self.args.search):
                if "spotify.com" in query:
                    self.download_by_url(query)
                else:
                    self.search(query)
        elif self.args.bulk_download:
            raise NotImplementedError()
            with open(self.args.bulk_download, "r") as file:
                for line in file:
                    for url in self.split_input(line.strip()):
                        self.download_by_url(url)
        else:
            raise NotImplementedError()
            while True:
                self.args.search = input("Search: ")
                while self.args.search == "":
                    logging.info("Please try again or press CTRL-C to terminate.")
                    self.args.search = input("Search: ")
                if self.args.search:
                    self.search(self.args.search)
                else:
                    logging.info("Invalid input")


def main():
    """Creates an instance of ZYSpotify"""
    zys = ZYSpotify()

    try:
        zys.start()
    except KeyboardInterrupt:
        logging.error("Interrupted by user")
        db_manager.commit()
        db_manager.close_all()
        sys.exit(0)


if __name__ == "__main__":
    main()
