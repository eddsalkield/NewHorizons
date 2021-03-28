from newhorizons.schemata import ChannelsResponse
import newhorizons.endpoints as ep
import httpx
from bs4 import BeautifulSoup
from calmjs.parse import es5
from calmjs.parse.walkers import Walker
from calmjs.parse.asttypes import VarDecl
from calmjs.parse.exceptions import ECMASyntaxError

import pdb

walker = Walker()   # Should this be constructed outside extract_channel?

def extract_yt_initial_data(soup) -> dict:
    """
    Extract the object bound to variable ytInitialData in a script tag
    """
    initial_data = {}
    for scripts in soup.find_all('script', src=None):
        for script in scripts.contents:
            # For some reason, YouTube sometimes serves scripts of the form
            # of an unbound object, which is invalid ECMAScript...
            # Actually it's probably just a type="application/ld+json"
            # Time to whitelist... https://www.iana.org/assignments/media-types/media-types.xhtml
            try:
                program = es5(script)
            except ECMASyntaxError as e:
                print('parsing failed, continuing')
                pdb.set_trace()
                continue

            # If you patch calmjs for this, fix typo "Initialisere":
            # https://github.com/calmjs/calmjs.parse/blob/e5998ef618a2abdd79c0dec44a1dc58df7c2538f/src/calmjs/parse/parsers/es5.py#L424
            # What are GetPropAssign and SetPropAssign for?
            # A: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/get
            # In essence, we don't have to worry about them

            # Keys in the object can either be string or a symbol value:
            #  https://stackoverflow.com/questions/65892079/what-are-the-valid-characters-values-allowed-as-keys-in-javascript-object
            for node in walker.filter(program, lambda node: (
                    isinstance(node, VarDecl) and
                    node.identifier.value == 'ytInitialData')):
                pass
                #for child in node.children[1].children():
                #    key = child.left.value
                    #value = 
                    

                print(node.identifier)
                pdb.set_trace()

async def extract_channel(ucid: str) -> ChannelsResponse:
    channel_type = 'channel' if len(ucid) == 24 and ucid[:2] == 'UC' else 'user'
    r = httpx.get(ep.channel_url.format(channel_type, ucid))
    soup = BeautifulSoup(r.text, 'html.parser')
    initial_data = extract_yt_initial_data(soup)


