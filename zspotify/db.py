import sqlite3
from typing import Any
from datetime import datetime
from pathlib import Path
from .types import SpotifyArtistId

CREATE_ARTISTS_TABLE = """
CREATE TABLE IF NOT EXISTS artists (
	artist_id TEXT NOT NULL PRIMARY KEY,
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL DEFAULT 0,
    timestamp_completed TIMESTAMP NOT NULL
);
"""

CREATE_ALBUMS_TABLE = """
CREATE TABLE IF NOT EXISTS albums (
	album_id TEXT NOT NULL PRIMARY KEY,
	artist_id TEXT NOT NULL,
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL DEFAULT 0,
    timestamp_completed TIMESTAMP NOT NULL,
    full_filepath TEXT,
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
    timestamp_completed TIMESTAMP NOT NULL,
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

    def have_all_liked_artists(self) -> bool:
        fetched = self.cursor.execute(
            "SELECT have_fetched_all_artists FROM fetched_artists"
        ).fetchone()
        if fetched is None or fetched[0] == 0:
            return False
        else:
            return True

    def get_all_liked_artists(self) -> list[SpotifyArtistId]:
        return self.cursor.execute("SELECT artist_id FROM artists").fetchall()

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
    def store_all_liked_artists(self, ):
        ...

    def commit(self) -> None:
        self.connection.commit()

    def close_all(self) -> None:
        self.cursor.close()
        self.connection.close()

    def test(self):
        self.cursor.execute(
            "UPDATE artists SET artist_id = ? WHERE artists.artist_id = ?",
            ("aaa", "abc123"),
        )


db_manager = SQLiteDBManager()

print(db_manager.have_all_liked_artists())
db_manager.set_have_all_liked_artist(False, should_commit=True)

print(db_manager.have_all_liked_artists())
# db_manager.insert_one_into_artists(("abc128899", "tradddvis", 0, datetime.now()))
# db_manager.insert_one_into_albums(("albbffd", "abc128899", "crazyalmb", 0, datetime.now(), "/home/mus"))
# db_manager.insert_one_into_songs(("song1", "albbffd", "abc128899", 320, "cool", 1, datetime.now(), "/home/ms"))
# # db_manager.test()
# db_manager.commit()
# db_manager.close_all()
