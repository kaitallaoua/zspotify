SpotifyArtistId = str
ArtistName = str
PackedArtist = tuple[SpotifyArtistId, ArtistName]
PackedArtists = list[PackedArtist]
ArtistInfo = dict[str, str]

SpotifyAlbumId = str
SpotifyAlbumName = str
PackedAlbums = list[dict[SpotifyAlbumId, SpotifyAlbumName]]

SpotifySongId = str
PackedSongs = list[dict[str, str | int]]

Credentials = tuple[str, str, str]
