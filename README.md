# ZYSpotify

[![GPLv3](https://img.shields.io/github/license/jsavargas/zspotify)](https://opensource.org/license/gpl-3-0)

This is a moderately modifed fork of ZSpotify with the goal of more robust large downloads (sqlite db instead of json archive file), eventually with the purpose to be run periodically/as a service to fetch new songs and more. A fork was decided as many, many changes were desired to be implemented more quickly than PR's.

Currently only a subset of switches are supported, but eventually should be feature matched to zspotify. Only the shown switches in the usage are what have been tested, others may work (if NotImplementedError is removed).

ZYSpotify is a Spotify downloader that enables users to find and download (a lot of) songs.

## Roadmap

- [x] Use sqlite3 db instead of json archive
- [x] Put credentials in db
- [ ] Verify switch to ignore artist/album/song fetched and artist+album download_completed atributes (but not song download_completed) to check, and download if missing, missed songs
- [ ] Add spotify liked songs playlist importer for plex
- [ ] Ensure pip install works
- [ ] Get all other switches working
- [ ] Use logging libary instead of printing
- [ ] Check for new artist songs/albums feature
- [ ] Ensure docker support works
- [ ] Conform project for strict type checking
- [ ] Use code coverage/test suites



## Installation
### Recommended: use virtual enviroments
Clone the repo, pip install the requirements and follow the usage below

## Usage

```
usage: zyspotify [-h] [-lsdall] [-md MUSIC_DIR] [--antiban-time ANTIBAN_TIME] [--antiban-album ANTIBAN_ALBUM] [-f]

options:
  -h, --help            show this help message and exit
  -lsdall, --all-liked-all-artists
                        Download all songs from all (main) artists that appear in your liked songs
  -f, --force-premium   Force premium account
  -md MUSIC_DIR, --music-dir MUSIC_DIR
                        Folder to save the downloaded music files
```

## Changelog

[View changelog here](https://github.com/kaitallaoua/zyspotify/blob/master/CHANGELOG.md)

## Disclaimer

It is recommended to use a burner account to avoid any possible account bans.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

- [GitHub Issues](https://github.com/kaitallaoua/zyspotify/issues) of this repository.
- [Discussions](https://github.com/kaitallaoua/zyspotify/discussions) of this repository.

## Acknowledgements

- [Footsiefat](https://github.com/Footsiefat) for original ZSpotify implementation
- [jsavargas](https://github.com/jsavargas/zspotify) for the latest forked version