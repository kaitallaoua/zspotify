# ZSpotify

[![Docker CI](https://github.com/jsavargas/zspotify/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/jsavargas/zspotify/actions/workflows/docker-ci.yml)
[![GPLv3](https://img.shields.io/github/license/jsavargas/zspotify)](https://opensource.org/license/gpl-3-0)

ZSpotify is a Spotify downloader that enables users to find and download songs.


## Installation

Install ZSpotify using either [pip](#pip) or [Docker](#docker)

### pip

1. **Install required dependencies:**
    - Python (3.10 or greater)
        - [Python download (Windows)](https://www.python.org/downloads/)
    - FFmpeg
        - [FFmpeg download (Windows)](https://ffmpeg.org/download.html)
        - [FFmpeg installation guide (Windows)](https://www.wikihow.com/Install-FFmpeg-on-Windows)
   > :warning: To install Python and FFmpeg on **Linux**, use the preferred package manager for your distribution.

2. **Install ZSpotify:**

```bash
pip install git+https://github.com/jsavargas/zspotify
```

### Docker

```bash
docker pull jsavargas/zspotify
docker run -v ${HOME}/.zspotify:/root/.zspotify -v ${HOME}/Music:/root/Music -it jsavargas/zspotify
```
***PLEASE NOTE 🗒️***
You must first run zspotify locally and authenticate. Migrate your authentication file (credentials.json) into the .zspotify volume on your docker system so that it can be used on start.  
  Otherwise your Docker run will fail due to it trying to recieve a username input that it will never get.



## Usage

```
usage: zspotify [-h] [-ap] [-sp] [-ls] [-pl PLAYLIST] [-tr TRACK] [-al ALBUM] [-ar ARTIST] [-ep EPISODE]
                [-fs FULL_SHOW] [-cd CONFIG_DIR] [--archive ARCHIVE] [-d DOWNLOAD_DIR] [-md MUSIC_DIR]
                [-pd EPISODES_DIR] [-v] [-af {mp3,ogg}] [--album-in-filename] [--antiban-time ANTIBAN_TIME]
                [--antiban-album ANTIBAN_ALBUM] [--limit LIMIT] [-f] [-ns] [-s] [-cf CREDENTIALS_FILE]
                [-bd BULK_DOWNLOAD]
                [search]

positional arguments:
  search                Searches for a track, album, artist or playlist or download by url

options:
  -h, --help            Show this help message and exit
  -v, --version         Shows the current version of ZSpotify
  -ap, --all-playlists  Downloads all saved playlist from your library
  -sp, --select-playlists
                        Downloads a saved playlist from your library
  -ls, --liked-songs    Downloads your liked songs
  -pl PLAYLIST, --playlist PLAYLIST
                        Download playlist by id or url
  -tr TRACK, --track TRACK
                        Downloads a track from their id or url
  -al ALBUM, --album ALBUM
                        Downloads an album from their id or url
  -ar ARTIST, --artist ARTIST
                        Downloads an artist from their id or url
  -ep EPISODE, --episode EPISODE
                        Downloads a episode from their id or url
  -fs FULL_SHOW, --full-show FULL_SHOW
                        Downloads all show episodes from id or url
  -cd CONFIG_DIR, --config-dir CONFIG_DIR
                        Folder to save the config files  
                        Default: *nix => $HOME/.zspotify Windows => (%homepath%)/.zspotify
  --archive ARCHIVE     File to save the downloaded files
  -d DOWNLOAD_DIR, --download-dir DOWNLOAD_DIR
                        Folder to save the downloaded files
  -md MUSIC_DIR, --music-dir MUSIC_DIR
                        Folder to save the downloaded music files
  -pd EPISODES_DIR, --episodes-dir EPISODES_DIR
                        Folder to save the downloaded episodes files
  -af {mp3,ogg}, --audio-format {mp3,ogg}
                        Audio format to download the tracks
  --album-in-filename   Adds the album name to the filename
  --antiban-time ANTIBAN_TIME
                        Time (seconds) to wait between downloads to avoid Ban
  --antiban-album ANTIBAN_ALBUM
                        Time (seconds) to wait between album downloads to avoid Ban
  --limit LIMIT         Search Limit (seconds)
                        Imposes a search limit that is overridable with the environment variable LIMIT_RESULTS
                        Default: 10
  -f, --force-premium   Force premium account
  -ns, --not-skip-existing
                        If flag setted NOT Skip existing already downloaded tracks
  -s, --skip-downloaded
                        Skip already downloaded songs if exist in archive even it is doesn't exist in the filesystem
  -cf CREDENTIALS_FILE, --credentials-file CREDENTIALS_FILE
                        File to save the credentials  
                        Run once to create this file with your terminal input username and password.   
                        Then move the file and change the directory with this argument.
  -bd BULK_DOWNLOAD, --bulk-download BULK_DOWNLOAD
                        Bulk download from file with urls
```

## Changelog

[View changelog here](https://github.com/jsavargas/zspotify/blob/master/CHANGELOG.md)

## Disclaimer

We recommend using a burner account to avoid any possible account bans.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

- [GitHub Issues](https://github.com/jsavargas/zspotify/issues) of this repository.
- [DockerHub](https://hub.docker.com/r/jsavargas/zspotify) of this repository.
- [Discord](https://discord.gg/grCt4AufmC) server of this repository.

## Acknowledgements

- [Footsiefat](https://github.com/Footsiefat) for original ZSpotify implementation
