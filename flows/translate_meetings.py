from prefect import flow

from tasks.meetings import create_meetings_csv


@flow(log_prints=True)
async def translate_meetings():
    await create_meetings_csv()
    # TODO: await download_videos()
    # TODO: await transcribe_videos()
    # TODO: await diarize_transcriptions()
    # TODO: await translate_transcriptions()
    # TODO: await create_subtitled_video_pages()

if __name__ == "__main__":
    import asyncio
    asyncio.run(translate_meetings())
