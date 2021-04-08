import re

# TODO: support other language endpoints
# TODO: rename to constants?

# General
consent_cookies = {"CONSENT": "PENDING+999"}

# Channel
channel_url = 'https://www.youtube.com/{}/{}/videos?hl=en'
channel_feed = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'
author_thumbnail_sizes = [32, 48, 76, 100, 176, 512]
