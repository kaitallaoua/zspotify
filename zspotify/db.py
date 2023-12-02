# from .types import SpotifyArtistId

import sqlite3
from typing import Any
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
    quality_kbps INTEGER NOT NULL,
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL DEFAULT 0,
    timestamp_completed TIMESTAMP DEFAULT NULL,
    full_filepath TEXT,
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


class SQLiteDBManager:
    def __init__(self) -> None:
        self.create_db()

    def create_db(self, db_dir: Path = Path.cwd() / "config"):
        Path.mkdir(db_dir, parents=True, exist_ok=True)

        self.connection = sqlite3.connect(
            db_dir / "zspotify.db",
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self.connection.execute("PRAGMA foreign_keys = 1")

        self.cursor = self.connection.cursor()
        self.cursor.execute(CREATE_ARTISTS_TABLE)
        self.cursor.execute(CREATE_ALBUMS_TABLE)
        self.cursor.execute(CREATE_SONGS_TABLE)
        self.cursor.execute(CREATE_FETCHED_ARTISTS_TABLE)
        self.cursor.execute(CREATE_FETCHED_ARTIST_ALBUMS_TABLE)
        self.connection.commit()

    def insert_one_into_artists(
        self, value: tuple[str, str, int, datetime], should_commit: bool = False
    ) -> None:
        self.cursor.execute("INSERT INTO artists VALUES (?, ?, ?, ?)", value)

        if should_commit:
            self.connection.commit()

    def insert_one_into_albums(
        self,
        value: tuple[str, str, str, int, datetime, str],
        should_commit: bool = False,
    ) -> None:
        self.cursor.execute("INSERT INTO albums VALUES (?, ?, ?, ?, ?, ?)", value)

        if should_commit:
            self.connection.commit()

    def insert_one_into_songs(
        self,
        value: tuple[str, str, str, int, str, int, datetime, str],
        should_commit: bool = False,
    ) -> None:
        self.cursor.execute("INSERT INTO songs VALUES (?, ?, ?, ?, ?, ?, ?, ?)", value)

        if should_commit:
            self.connection.commit()

    def have_all_artist_albums(self, artist_id: SpotifyArtistId):
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
                "INSERT INTO albums (album_id, artist_id, name) VALUES (?, ?, ?)",
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
        self.cursor.executemany(
            "INSERT INTO artists (artist_id, name) VALUES (?, ?)", packed_artists
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


db_manager = SQLiteDBManager()
# a = [("3QJzdZJYIAcoET1GcfpNGi", "damain marley"), ("7lZauDnRoAC3kmaYae2opv", "Dabin"), ("3QJzdZJYIAcoET1GcfpNGi", "damain marley")]

# def removeDuplicates(lst):

#     return [t for t in (set(tuple(i) for i in lst))]

# s = sorted(removeDuplicates(a))

# db_manager.store_all_liked_artists(s, should_commit=True)
# # print(db_manager.have_all_liked_artists())
# # db_manager.set_have_all_liked_artist(False, should_commit=True)

# # print(db_manager.have_all_liked_artists())
# # db_manager.insert_one_into_artists(("abc128899", "tradddvis", 0, datetime.now()))
# # db_manager.insert_one_into_albums(("albbffd", "abc128899", "crazyalmb", 0, datetime.now(), "/home/mus"))
# # db_manager.insert_one_into_songs(("song1", "albbffd", "abc128899", 320, "cool", 1, datetime.now(), "/home/ms"))
# # # db_manager.test()
# db_manager.commit()
# db_manager.close_all()
