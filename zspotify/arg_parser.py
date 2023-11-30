import argparse
from pathlib import Path
import os

_ANTI_BAN_WAIT_TIME = os.environ.get("ANTI_BAN_WAIT_TIME", 5)
_ANTI_BAN_WAIT_TIME_ALBUMS = os.environ.get("ANTI_BAN_WAIT_TIME_ALBUMS", 30)
_LIMIT_RESULTS = os.environ.get("LIMIT_RESULTS", 10)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "search",
        help="Searches for a track, album, artist or playlist or download by url",
        const=None,
        nargs="?",
    )
    parser.add_argument(
        "-ap",
        "--all-playlists",
        help="Downloads all saved playlist from your library",
        action="store_true",
    )
    parser.add_argument(
        "-sp",
        "--select-playlists",
        help="Downloads a saved playlist from your library",
        action="store_true",
    )
    parser.add_argument(
        "-ls",
        "--liked-songs",
        help="Downloads your liked songs",
        action="store_true",
    )
    parser.add_argument(
        "-lsdall",
        "--all-liked-all-artists",
        help="Download all songs from all (main) artists that appear in your liked songs",
        action="store_true",
    )
    parser.add_argument("-pl", "--playlist", help="Download playlist by id or url")
    parser.add_argument("-tr", "--track", help="Downloads a track from their id or url")
    parser.add_argument(
        "-al", "--album", help="Downloads an album from their id or url"
    )
    parser.add_argument(
        "-ar", "--artist", help="Downloads an artist from their id or url"
    )
    parser.add_argument(
        "-ep", "--episode", help="Downloads a episode from their id or url"
    )
    parser.add_argument(
        "-fs", "--full-show", help="Downloads all show episodes from id or url"
    )
    parser.add_argument(
        "-cd",
        "--config-dir",
        help="Folder to save the config files",
        default=Path.home() / ".zspotify",
    )
    parser.add_argument(
        "--archive",
        help="File to save the downloaded files",
        default="archive.json",
    )
    parser.add_argument(
        "-d",
        "--download-dir",
        help="Folder to save the downloaded files",
        default=Path.home() / "Music",
    )
    parser.add_argument(
        "-md",
        "--music-dir",
        help="Folder to save the downloaded music files",
        default=Path.home() / "Music" / "ZSpotify Music",
    )
    parser.add_argument(
        "-pd",
        "--episodes-dir",
        help="Folder to save the downloaded episodes files",
        default=Path.home() / "Music" / "ZSpotify Podcast",
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Shows the current version of ZSpotify and exit",
        action="store_true",
    )
    parser.add_argument(
        "-af",
        "--audio-format",
        help="Audio format to download the tracks. Use 'source' to preserve the source format without conversion.",
        default="mp3",
        choices=["mp3", "ogg", "source"],
    )
    parser.add_argument(
        "--album-in-filename",
        help="Adds the album name to the filename",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--antiban-time",
        help="Time to wait between downloads to avoid Ban",
        default=_ANTI_BAN_WAIT_TIME,
        type=int,
    )
    parser.add_argument(
        "--antiban-album",
        help="Time to wait between album downloads to avoid Ban",
        default=_ANTI_BAN_WAIT_TIME_ALBUMS,
        type=int,
    )
    parser.add_argument(
        "--limit", help="Search limit", default=_LIMIT_RESULTS, type=int
    )
    parser.add_argument(
        "-f",
        "--force-premium",
        help="Force premium account",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-ns",
        "--not-skip-existing",
        help="If flag setted NOT Skip existing already downloaded tracks",
        action="store_false",
        default=True,
    )
    parser.add_argument(
        "-s",
        "--skip-downloaded",
        help="Skip already downloaded songs if exist in archive even it is doesn't exist in the filesystem",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-cf",
        "--credentials-file",
        help="File to save the credentials",
        default=Path.home() / ".zspotify" / "credentials.json",
    )
    parser.add_argument(
        "-bd", "--bulk-download", help="Bulk download from file with urls"
    )

    return parser.parse_args()
