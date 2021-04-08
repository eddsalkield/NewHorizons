from newhorizons.schemata import ChannelsResponse, AuthorThumbnail, AuthorBanner
from newhorizons.helpers import normalise_url_protocol
import newhorizons.endpoints as ep
import httpx
from bs4 import BeautifulSoup
from calmjs.parse import es5
from calmjs.parse.walkers import Walker
from calmjs.parse.asttypes import VarDecl
from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.parse.unparsers import extractor
from typing import Tuple, Any, Callable, Optional, TypeVar, Generic, Union, List
from functools import partial
from urllib.parse import urlparse
import re
from pydantic import ValidationError

# DEBUG- TODO delete
import pdb
from pprint import pprint

walker = Walker()

def extract_yt_initial_data(soup: BeautifulSoup) -> dict:
    """
    Extract the object bound to variable ytInitialData in a script tag
    """
    initial_data = {}
    for scripts in soup.find_all('script', src=None, type=None):
        for script in scripts.contents:
            try:
                program = es5(script)
            except ECMASyntaxError as e:
                # TODO: proper logging
                print('DEBUG: parsing failed, continuing')
                continue

            for node in walker.filter(program, lambda node: (
                    isinstance(node, VarDecl) and
                    node.identifier.value == 'ytInitialData')):
                new_data = next(extractor.build_dict(node.initializer))
                obj = node.initializer
                initial_data = {**initial_data, **new_data}
    return initial_data

class _AssertExists:
    pass

# TODO: Not required any more?
T = TypeVar('T')
def fallback(default: T) -> Callable[[], T]:
    # TODO: replace with proper logging
    def f() -> T:
        print(f'DEBUG: {d_name} missing field {keys}')
        return default
    return f

def extract(d_name: str, d: Any, keys: Union[Tuple[Any], Any],
        default: Union[Callable[[], Any], Any] = _AssertExists(),
        process: Callable[[Any], Any] = lambda x: x,
        log_default: bool = True):
    """
    Extract from d the value at path keys and return it, \
    optionally processing it with the function process.
    If the value within d cannot be found, and a default was provided, return it \
    and log that the field was missing.
    If the value within d cannot be found, and no default was provided, raise \
    a ValidationError.
    If d is not a dict, return the default.

    process can be used to typecheck, since any TypeError raised gets logged.
    """
    # Permit conditioning on the dict not existing
    if not isinstance(d, dict):
        if isinstance(default, _AssertExists):
            raise ValueError(f'{d_name} is not a dict and no default given')
        return default() if callable(default) else default

    if isinstance(keys, tuple):
        try:
            data_field = d
            for k in keys:
                if not data_field:
                    break
                data_field = data_field[k]
        except KeyError:
            if isinstance(default, _AssertExists):
                raise ValueError(
                    f'{d_name} missing field {keys} and no default given')
            else:
                # TODO: replace with proper logging
                if log_default:
                    print(f'DEBUG: {d_name} missing field {keys}')
                return default() if callable(default) else default
    else:
        data_field = d[keys]

    try:
        return process(data_field)
    except ValidationError as e:
        # TODO: replace with proper logging
        print(f'DEBUG: {d_name} raised TypeError {e}')
        if isinstance(default, _AssertExists):
            raise ValueError(f'{d_name} raised TypeError {e} and no default given')
        return default() if callable(default) else default

# Create and typecheck an author banner
def process_banner(banner: AuthorBanner) -> AuthorBanner:
    """
    Typecheck and normalise the URL of an author banner.
    """
    banner = AuthorBanner(**banner)
    banner.url = normalise_url_protocol(banner.url)
    return banner

# TODO: I've found additional thumbnails of size 88.  Is this globally consistent?
# Should we check that these thumbnails exist?  If so, we could pre-emptively
# add them to the cache (when I get around to implementing the cache)
# TODO: export these to a constants file?
# TODO: log if the Match object from the re does now have length 1
def generate_full_author_thumbnails(thumbnails: List[dict]) \
        -> List[AuthorThumbnail]:
    """
    Typecheck and parse list of author thumbnails to include the full set of sizes.
    Assume that all thumbnails in the list refer to the same base image.
    Assume that all thumbnails we can generate have width == height.
    """
    thumbnail_size_regex = re.compile(r'=s[0-9]+-')
    thumbnails = list(map(lambda t: AuthorThumbnail(**t), thumbnails))
    if thumbnail_size_regex.search(thumbnails[0].url):
        url_template = re.sub(thumbnail_size_regex, '=s{}-', thumbnails[0].url)
        existing_sizes = list(map(lambda t: \
                    int(thumbnail_size_regex.search(t.url)[0][2:-1]),
                thumbnails))
        thumbnails = [
                AuthorThumbnail(**{
                    'url': url_template.format(size),
                    'width': size,
                    'height': size
                }) for size in ep.author_thumbnail_sizes
                if size not in existing_sizes] + thumbnails
    return thumbnails

async def extract_channel(ucid: str) -> ChannelsResponse:
    channel_type = 'channel' if len(ucid) == 24 and ucid[:2] == 'UC' else 'user'
    r = httpx.get(ep.channel_url.format(channel_type, ucid), cookies={**ep.consent_cookies})
    soup = BeautifulSoup(r.text, 'html.parser')
    initial_data = extract_yt_initial_data(soup)
    extract_initial = partial(extract, 'initial_data', initial_data)

    header = extract_initial(('header', 'c4TabbedHeaderRenderer',), None)
    extract_header = partial(extract, 'header', header)
    metadata = extract_initial(('metadata', 'channelMetadataRenderer',), None)
    extract_metadata = partial(extract, 'metadata', metadata)

    # Workspace
    try:
        author_thumbnails = generate_full_author_thumbnails(
            extract_header(('avatar', 'thumbnails',), []) + \
                extract_metadata(('avatar', 'thumbnails',), []))
    except ValidationError as e:
        # TODO: replace with proper logging
        print(f'DEBUG: {d_name} raised TypeError {e}')
        author_thumbnails = []

    channel = {
        'author': extract_header('title',
                lambda: extract_metadata('title', fallback(None))),
        'authorId': extract_header('channelId',
                lambda: extract_metadata('externalId', fallback(None))),
        'authorUrl': extract_header(('navigationEndpoint', 'commandMetadata',
                                     'webCommandMetadata', 'url'),
                lambda: extract_metadata('channelUrl', fallback(None))),
        'authorBanners': extract_header(('banner', 'thumbnails',), [], 
                                lambda l: list(map(process_banner, l))),
        'authorThumbnails': author_thumbnails,

        'subCount': None,
        'totalViews': None,
        'joined': None,

        'paid': None,
        'autoGenerated': None,
        'isFamilyFriendly': None,
        'description': None,
        'descriptionHtml': None,
        'allowedRegions': None,

        'latestVideos': None,
        'relatedChannels': None,
    }
    return ChannelsResponse(**channel)
