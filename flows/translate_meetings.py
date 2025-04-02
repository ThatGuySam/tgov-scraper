from prefect import flow

from tasks.meetings import get_new_meetings


@flow(log_prints=True)
async def translate_meetings():
    new_meetings = await get_new_meetings()
    # new_transcribed_meetings = await transcribe_videos(new_meetings)
    # new_subtitled_video_pages = await create_subtitled_video_pages(new_transcribed_meetings)
    # new_translated_meetings = await translate_transcriptions(new_transcribed_meetings)

if __name__ == "__main__":
    import asyncio
    asyncio.run(translate_meetings())
