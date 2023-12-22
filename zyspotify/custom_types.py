SpotifyArtistId = str
ArtistName = str
PackedArtists = list[tuple[SpotifyArtistId, ArtistName]]

SpotifyAlbumId = str
SpotifyAlbumName = str
PackedAlbums = list[dict[SpotifyAlbumId, SpotifyAlbumName]]

SpotifySongId = str
PackedSongs = list[dict[str, str | int]]

Credentials = tuple[str, str, str]
