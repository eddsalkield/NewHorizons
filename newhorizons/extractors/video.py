from typing import Union
from newhorizons.schemata import VideosResponse, AdaptiveFormat, FormatStream, Caption
import youtube_dl
from datetime import datetime

ydl_opts = {
#    'quiet': True,
#    'dump_single_json': True,
#    "playlist_items": "1-100",
#    "extract_flat": "in_playlist",
#    "write_pages": True,
#    "source_address": "0.0.0.0",
#    "writesubtitles": True,
#    "allsubtitles": True
}

ydl = youtube_dl.YoutubeDL(ydl_opts)


def is_adaptive(format: dict) -> bool:
    """
    Return true if format is adaptive, false if it's a format stream
    Adaptive formats have either audio or video, format streams have both
    """
    return format['acodec'] == 'none' or format['vcodec'] == 'none'

# TODO: evaluate how much of the possible info this captures
def generate_format(format: dict) -> Union[AdaptiveFormat, FormatStream]:
    # TODO: check out if format 'none' exists
    # Doesn't seem to here:
    # https://github.com/ytdl-org/youtube-dl/blob/c78591187080e7316c0042309fe956bfd0d38d30/youtube_dl/postprocessor/ffmpeg.py#L39

    result_type = '{}/{}; codecs="{}"'.format(
        'audio' if format['vcodec'] == 'none' else 'video',
        format['ext'],
        ', '.join(filter(lambda x: x != 'none',
                            [format['vcodec'], format['acodec']]))
    )

    if is_adaptive(format):
        if format['protocol'] == 'http_dash_segments':
            # TODO: review
            # this is http dash, which is annoying and doesn't work in <video>.
            # we have a fragment_base_url, which seems to be playable for all audio, but only with certain video itags??? very confused
            # This does some magic that I don't understand
            if format['acodec'] == 'none' and format['format_id'] not in ['134', '136']:
                return None
            url = format['fragment_base_url']
        else:
            # regular media file
            url = format['url']

        return AdaptiveFormat(**{
            'index': None,
            'bitrate': str(int(format['tbr']*1000)),
            'init': None,
            'url': url,
            'itag': format['format_id'],
            'type': result_type,
            #'second__mime'
            #'second__codecs'
            'clen': str(format['filesize']) if format['filesize'] else None, # is it permissible to return None here?
            'lmt': None,
            'projectionType': None,
            #'fps': format['fps']
            'container': format['ext'],
            'encoding': None,
            'qualityLabel': format['format_note'],
            'resolution': format['format_note'],
            #'second__width': format['width'],
            #'second__height': format['height'],
            #'second__audioChannels': None,
            #'second__order': 0
        })
    else:
        return FormatStream(**{
            'url': format['url'],
            'itag': format['format_id'],
            'type': result_type,
            #'second__mime': mime,
            'quality': None,
            #'fps': format['fps'],
            'container': format['ext'],
            'encoding': None,
            'qualityLabel': format['format_note'],
            'resolution': format['format_note'],
            'size': str(format['width']) + 'x' + str(format['height']),
            #'second__width': format['width'],
            #'second__height': format['height']
        })

def generate_caption(language_code: str, subtitle: dict) -> Caption:
    if language_code == 'live_chat':
        return None

    return Caption(**{
        'label': language_code if label == '' else None, # TODO: get_language_label_from_url(subtitle['url'])
        'languageCode': language_code,
        'url': None # TODO: get subtitle_api_url
        #"second__subtitleUrl": subtitle_url # Direct YouTube URL
    })

async def extract_video(id: str) -> VideosResponse:
    info = ydl.extract_info(id, download=False)
    upload_date = datetime.strptime(info['upload_date'], '%Y%m%d')

    
    adaptive_formats = []
    format_streams = []
    # TODO: async for?
    for format in info['formats']:
        f = generate_format(format)
        if isinstance(f, AdaptiveFormat):
            adaptive_formats.append(f)
        elif isinstance(f, FormatStream):
            format_streams.append(f)

    captions = []
    if subtitles := info.get('requested_subtitles'):
        captions = filter(lambda x: x is not None,
                [generate_caption(language_code, subtitle) 
                    for language_code, subtitle in subtitles])

    return VideosResponse(**{
        'title': info['title'],
        'videoId': info['id'],
        'videoThumbnails': [],  # TODO: implement. Extract from info['thumbnails']
        'description': info['description'],
        'descriptionHtml': None, # TODO: implement WITHOUT REGEX PARSING
        'published': upload_date.timestamp(),
        'publishedText': None,
        'keywords': info['tags'],
        'viewCount': info['view_count'],
        #"second__viewCountText": None,
        #"second__viewCountTextShort": None,
        'likeCount': info['like_count'],
        'dislikeCount': info['dislike_count'],
        'paid': None,
        'premium': None,
        'isFamilyFriendly': None, # TODO: could this be extracted from info['age_limit']?
        'allowedRegions': None,
        'genre': info['categories'][0] if info['categories'] is not [] else None, # This is a guess
        'genreUrl': None,
        'author': info['uploader'],
        'authorId': info['channel_id'],
        'authorUrl': info['channel_url'],
        #"second__uploaderId": info["uploader_id"],
        #"second__uploaderUrl": info["uploader_url"],
        'authorThumbnails': [], # TODO
        'subCountText': None,
        'lengthSeconds': info['duration'],
        'allowRatings': None,
        'rating': info['average_rating'],
        'isListed': None,
        'liveNow': None,
        'isUpcoming': None,
        'premiereTimestamp': None,
        'hlsUrl': None,
        'adaptiveFormats': adaptive_formats,
        'formatStreams': format_streams,
        'captions': captions,
        'recommendedVideos': [],
        #'dashurl': # Implement, if it turns out it's required
        #"second__providedDashUrl": None,
    })
