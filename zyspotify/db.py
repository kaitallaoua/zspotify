# from .types import SpotifyArtistId

import sqlite3
from typing import Optional
from datetime import datetime
from pathlib import Path

from .custom_types import *

CREATE_ARTISTS_TABLE = """
CREATE TABLE IF NOT EXISTS artists (
	artist_id TEXT NOT NULL PRIMARY KEY,
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL DEFAULT 0,
    timestamp_completed TIMESTAMP DEFAULT NULL
);
"""

CREATE_ALBUMS_TABLE = """
CREATE TABLE IF NOT EXISTS albums (
	album_id TEXT NOT NULL PRIMARY KEY,
	artist_id TEXT NOT NULL,
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL DEFAULT 0,
    timestamp_completed TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (artist_id) 
  	REFERENCES artists (artist_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE
);
"""

CREATE_SONGS_TABLE = """
CREATE TABLE IF NOT EXISTS songs (
	song_id TEXT NOT NULL PRIMARY KEY,
	album_id TEXT NOT NULL,
	artist_id TEXT NOT NULL,
	name TEXT NOT NULL,
    track_number INTEGER NOT NULL,
    disc_number INTEGER NOT NULL,
    quality_kbps INTEGER NOT NULL,
    full_filepath TEXT DEFAULT NULL,
    download_completed INTEGER NOT NULL DEFAULT 0,
    timestamp_completed TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (artist_id) 
    REFERENCES artists (artist_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE,
    FOREIGN KEY (album_id) 
    REFERENCES albums (album_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE
);
"""

# check for primary key id = 0 to ensure only one row can exist
CREATE_FETCHED_ARTISTS_TABLE = """
CREATE TABLE IF NOT EXISTS fetched_artists (
    id INTEGER PRIMARY KEY CHECK (id = 0),
    have_fetched_all_artists INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_FETCHED_ARTIST_ALBUMS_TABLE = """
CREATE TABLE IF NOT EXISTS fetched_albums (
	artist_id TEXT PRIMARY KEY NOT NULL,
    have_fetched_all_albums INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (artist_id) 
    REFERENCES artists (artist_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE
);
"""

CREATE_FETCHED_ALBUM_SONGS_TABLE = """
CREATE TABLE IF NOT EXISTS fetched_songs (
	album_id TEXT PRIMARY KEY NOT NULL,
    have_fetched_all_songs_in_album INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (album_id) 
    REFERENCES albums (album_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE
);
"""

CREATE_CREDENTIALS_TABLE = """
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY CHECK (id = 0),
    username TEXT NOT NULL,
    credentials TEXT NOT NULL,
    type TEXT NOT NULL
);
"""


class SQLiteDBManager:
    def __init__(self) -> None:
        ...

    def create_db(self, db_dir: Path):
        Path.mkdir(db_dir, parents=True, exist_ok=True)

        self.connection = sqlite3.connect(
            db_dir / "zyspotify.db",
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self.connection.execute("PRAGMA foreign_keys = 1")

        self.cursor = self.connection.cursor()
        self.cursor.execute(CREATE_ARTISTS_TABLE)
        self.cursor.execute(CREATE_ALBUMS_TABLE)
        self.cursor.execute(CREATE_SONGS_TABLE)
        self.cursor.execute(CREATE_FETCHED_ARTISTS_TABLE)
        self.cursor.execute(CREATE_FETCHED_ARTIST_ALBUMS_TABLE)
        self.cursor.execute(CREATE_FETCHED_ALBUM_SONGS_TABLE)
        self.cursor.execute(CREATE_CREDENTIALS_TABLE)
        self.connection.commit()

    def have_all_artist_albums(self, artist_id: SpotifyArtistId) -> bool:
        fetched = self.cursor.execute(
            "SELECT have_fetched_all_albums FROM fetched_albums WHERE artist_id = ?",
            (artist_id,),
        ).fetchone()
        if fetched is None or fetched[0] == 0:
            return False
        else:
            return True

    def store_all_artist_albums(
        self,
        artist_id: SpotifyArtistId,
        packed_albums: PackedAlbums,
        should_commit: bool = False,
    ):
        for album in packed_albums:
            self.cursor.execute(
                "INSERT OR IGNORE INTO albums (album_id, artist_id, name) VALUES (?, ?, ?)",
                (album["id"], artist_id, album["name"]),
            )
        if should_commit:
            self.connection.commit()

    def set_have_all_artist_albums(
        self, artist_id: SpotifyArtistId, value: bool, should_commit: bool = False
    ):
        param = (
            artist_id,
            int(value),
        )  # upsert, insert if none exists, overrite prior with new
        self.cursor.execute(
            """INSERT INTO fetched_albums 
               VALUES (?, ?) ON CONFLICT (artist_id) 
               DO UPDATE SET have_fetched_all_albums=excluded.have_fetched_all_albums""",
            param,
        )
        if should_commit:
            self.connection.commit()

    def get_all_artist_albums(self, artist_id: SpotifyArtistId) -> list[SpotifyAlbumId]:
        # you always get a tuple back, just need to index to the first value

        result = self.cursor.execute(
            "SELECT album_id FROM albums WHERE artist_id = ?", (artist_id,)
        ).fetchall()
        return [id[0] for id in result]

    def have_all_liked_artists(self) -> bool:
        fetched = self.cursor.execute(
            "SELECT have_fetched_all_artists FROM fetched_artists"
        ).fetchone()
        if fetched is None or fetched[0] == 0:
            return False
        else:
            return True

    def get_all_liked_artist_ids(self) -> list[SpotifyArtistId]:
        # you always get a tuple back, just need to index to the first value

        result = self.cursor.execute("SELECT artist_id FROM artists").fetchall()
        return [id[0] for id in result]

    def set_have_all_liked_artist(self, value: bool, should_commit: bool = False):
        param = (
            0,
            int(value),
        )  # upsert, insert if none exists, overrite prior with new
        self.cursor.execute(
            """INSERT INTO fetched_artists 
               VALUES (?, ?) ON CONFLICT (id) 
               DO UPDATE SET have_fetched_all_artists=excluded.have_fetched_all_artists""",
            param,
        )

        if should_commit:
            self.connection.commit()

    def store_all_liked_artists(
        self, packed_artists: list[PackedArtists], should_commit: bool = False
    ) -> None:
        
        # already inserted artists just ignore them
        self.cursor.executemany(
            "INSERT OR IGNORE INTO artists (artist_id, name) VALUES (?, ?)", packed_artists
        )

        if should_commit:
            self.connection.commit()

    def set_artist_fully_downloaded(
        self, artist_id: SpotifyArtistId, should_commit: bool = False
    ) -> None:
        self.cursor.execute(
            """UPDATE artists SET download_completed = ?, timestamp_completed = ? WHERE artist_id = ?""",
            (1, datetime.now().astimezone().isoformat(), artist_id),
        )
        if should_commit:
            self.connection.commit()

    def set_album_fully_downloaded(
        self, album_id: SpotifyAlbumId, should_commit: bool = False
    ) -> None:
        self.cursor.execute(
            """UPDATE albums SET download_completed = ?, timestamp_completed = ? WHERE album_id = ?""",
            (1, datetime.now().astimezone().isoformat(), album_id),
        )
        if should_commit:
            self.connection.commit()

    def have_artist_already_downloaded(self, artist_id: SpotifyArtistId) -> bool:
        fetched = self.cursor.execute(
            "SELECT download_completed FROM artists WHERE artist_id = ?", (artist_id,)
        ).fetchone()
        if fetched is None or fetched[0] == 0:
            return False
        else:
            return True

    def have_album_already_downloaded(self, album_id: SpotifyAlbumId) -> bool:
        fetched = self.cursor.execute(
            "SELECT download_completed FROM albums WHERE album_id = ?", (album_id,)
        ).fetchone()
        if fetched is None or fetched[0] == 0:
            return False
        else:
            return True

    def commit(self) -> None:
        self.connection.commit()

    def close_all(self) -> None:
        self.cursor.close()
        self.connection.close()

    def have_all_album_songs(self, album_id: SpotifyAlbumId) -> bool:
        fetched = self.cursor.execute(
            "SELECT have_fetched_all_songs_in_album FROM fetched_songs WHERE album_id = ?",
            (album_id,),
        ).fetchone()
        if fetched is None or fetched[0] == 0:
            return False
        else:
            return True

    def store_album_songs(
        self,
        packed_songs: PackedSongs,
        should_commit: bool = False,
    ):
        for song in packed_songs:
            self.cursor.execute(
                "INSERT OR IGNORE INTO songs (song_id, album_id, artist_id, name, track_number, disc_number, quality_kbps) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    song["id"],
                    song["album_id"],
                    song["artist_id"],
                    song["name"],
                    song["track_number"],
                    song["disc_number"],
                    song["quality_kbps"],
                ),
            )
        if should_commit:
            self.connection.commit()

    def set_have_album_songs(
        self, album_id: SpotifyAlbumId, value: bool, should_commit: bool = False
    ):
        param = (
            album_id,
            int(value),
        )  # upsert, insert if none exists, overrite prior with new
        self.cursor.execute(
            """INSERT INTO fetched_songs 
               VALUES (?, ?) ON CONFLICT (album_id) 
               DO UPDATE SET have_fetched_all_songs_in_album=excluded.have_fetched_all_songs_in_album""",
            param,
        )
        if should_commit:
            self.connection.commit()

    def get_album_songs(self, album_id: SpotifyAlbumId) -> list[PackedSongs]:
        # you always get a tuple back, just need to index to the first value

        results = self.cursor.execute(
            "SELECT song_id, album_id, artist_id, name, track_number, disc_number, quality_kbps FROM songs WHERE album_id = ?",
            (album_id,),
        ).fetchall()

        packed_songs = []

        for result in results:
            packed_songs.append(
                {
                    "id": result[0],
                    "album_id": result[1],
                    "artist_id": result[2],
                    "name": result[3],
                    "track_number": result[4],
                    "disc_number": result[5],
                    "quality_kbps": result[6],
                }
            )

        return packed_songs

    def set_song_downloaded(
        self, song_id: SpotifySongId, file_path: Path, should_commit: bool = False
    ) -> None:
        self.cursor.execute(
            """UPDATE songs SET full_filepath = ?, download_completed = ?, timestamp_completed = ? WHERE song_id = ?""",
            (
                file_path.as_posix(),
                1,
                datetime.now().astimezone().isoformat(),
                song_id,
            ),
        )
        if should_commit:
            self.connection.commit()

    def have_song_downloaded(self, song_id: SpotifySongId) -> bool:
        fetched = self.cursor.execute(
            "SELECT download_completed FROM songs WHERE song_id = ?", (song_id,)
        ).fetchone()
        if fetched is None or fetched[0] == 0:
            return False
        else:
            return True

    def upsert_credentials(
        self, username: str, credentials: str, type: str, should_commit: bool = False
    ) -> None:
        self.cursor.execute(
            """INSERT INTO credentials
               VALUES (?, ?, ?, ?) ON CONFLICT (id) 
               DO UPDATE SET username=excluded.username, credentials=excluded.credentials, type=excluded.type""",
            (0, username, credentials, type),
        )
        if should_commit:
            self.connection.commit()

    def has_stored_credentials(self) -> bool:
        return self.get_credentials() is not None

    def get_credentials(self) -> Optional[Credentials]:
        return self.cursor.execute(
            "SELECT username, credentials, type FROM credentials WHERE id = 0",
        ).fetchone()


db_manager = SQLiteDBManager()
