SpotifyArtistId = str
ArtistName = str
PackedArtists = list[tuple[SpotifyArtistId, ArtistName]]

SpotifyAlbumId = str
SpotifySongId = str
PackedAlbums = list[dict[str, str]]
PackedSongs = list[dict[str, str | int]]
