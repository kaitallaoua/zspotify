CREATE_ARTISTS_TABLE = """
CREATE TABLE IF NOT EXISTS artists (
	artist_id TEXT NOT NULL PRIMARY KEY,
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL,
    timestamp_completed TIMESTAMP,
);
"""

CREATE_ALBUMS_TABLE = """
CREATE TABLE IF NOT EXISTS albums (
	album_id TEXT NOT NULL PRIMARY KEY,
    FOREIGN KEY (artist_id) REFERENCES artists (artist_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL,
    timestamp_completed TIMESTAMP,
    full_filepath TEXT NOT NULL,
);
"""

CREATE_SONGS_TABLE = """
CREATE TABLE IF NOT EXISTS songs (
	song_id TEXT NOT NULL PRIMARY KEY,
    quality_kbps INTEGER NOT NULL,
    FOREIGN KEY (artist_id) REFERENCES artists (artist_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE
    FOREIGN KEY (album_id) REFERENCES albums (album_id)
       ON UPDATE CASCADE
       ON DELETE CASCADE
	name TEXT NOT NULL,
    download_completed INTEGER NOT NULL,
    timestamp_completed TIMESTAMP,
    full_filepath TEXT NOT NULL,
);
"""

class SQLiteDBManager:
    def __init__(self) -> None:
        self.create_db()

    def create_db(self, db_name: str = "zspotify.db"):
        ...
