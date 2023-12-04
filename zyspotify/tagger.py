import music_tag
import requests
from mutagen import id3

class AudioTagger:
    
    def __init__(self):
        pass

    def set_audio_tags(self, fullpath, artists=None, name=None, album_name=None, release_year=None,
                       disc_number=None, track_number=None, track_id_str=None, album_artist=None, image_url=None):
        """sets music_tag metadata using mutagen if possible"""
        
        album_artist = album_artist or artists  # Use artists if album_artist is None

        extension = str(fullpath).split('.')[-1]

        if extension == 'mp3':
            self._set_mp3_tags(fullpath, artists, name, album_name, release_year, disc_number,
                               track_number, track_id_str, album_artist, image_url)
        else:
            self._set_other_tags(fullpath, artists, name, album_name, release_year, disc_number,
                                 track_number, track_id_str, image_url)

    def _set_mp3_tags(self, fullpath, artist, name, album_name, release_year, disc_number, 
                      track_number, track_id_str, album_artist, image_url):
        tags = id3.ID3(fullpath)

        mp3_map = {
            "TPE1": artist,
            "TIT2": name,
            "TALB": album_name,
            "TDRC": release_year,
            "TDOR": release_year,
            "TPOS": str(disc_number) if disc_number else None,
            "TRCK": str(track_number) if track_number else None,
            "COMM": "https://open.spotify.com/track/" + track_id_str if track_id_str else None,
            "TPE2": album_artist,
        }

        for tag, value in mp3_map.items():
            if value:
                tags[tag] = id3.Frames[tag](encoding=3, text=value)

        if image_url:
            albumart = requests.get(image_url).content
            if albumart:
                tags["APIC"] = id3.APIC(encoding=3, mime="image/jpeg", type=3, desc="0", data=albumart)

        tags.save()

    def _set_other_tags(self, fullpath, artist, name, album_name, release_year, disc_number, 
                        track_number, track_id_str, image_url):
        tags = music_tag.load_file(fullpath)

        other_map = {
            "artist": artist,
            "tracktitle": name,
            "album": album_name,
            "year": release_year,
            "discnumber": str(disc_number) if disc_number else None,
            "tracknumber": track_number,
            "comment": "https://open.spotify.com/track/" + track_id_str if track_id_str else None
        }

        for tag, value in other_map.items():
            if value:
                tags[tag] = value

        if image_url:
            albumart = requests.get(image_url).content
            if albumart:
                tags["artwork"] = albumart

        tags.save()
