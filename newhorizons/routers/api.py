from fastapi import APIRouter, Depends
from newhorizons.schemata import VideosResponse, ChannelsResponse
from newhorizons.extractors.video import extract_video
from newhorizons.extractors.channel import extract_channel

router = APIRouter()


@router.get('/videos/{id}', response_model=VideosResponse)
async def videos(video_results = Depends(extract_video)):
    # TODO: cache the response
    return video_results

@router.get('/channels/{ucid}', response_model=ChannelsResponse)
async def channels(channel_results = Depends(extract_channel)):
    # TODO: cache the response
    return channel_results
