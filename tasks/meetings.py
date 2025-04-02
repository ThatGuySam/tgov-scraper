import os

import pandas as pd
from prefect import task

from src.aws import create_bucket_if_not_exists, is_aws_configured, upload_to_s3
from src.meetings import duration_to_minutes, get_meetings


file_path = 'data/meetings.csv'  # Path where the file will be saved locally temporarily
meetings_bucket_name = 'tgov-meetings'

@task
async def create_meetings_csv():
    meetings = await get_meetings()
    print(f"Got meetings: {meetings}")
    meeting_dicts = [meeting.model_dump() for meeting in meetings]
    print(f"meeting_dicts: {meeting_dicts}")
    df = pd.DataFrame(meeting_dicts)
    df['duration_minutes'] = df['duration'].apply(duration_to_minutes)
    df.to_csv(file_path, index=False)

    if is_aws_configured():
        print(f"file_path: {file_path}")
        create_bucket_if_not_exists(meetings_bucket_name)
        if not upload_to_s3(file_path, meetings_bucket_name, file_path):
            raise RuntimeError("Failed to upload to S3")
        os.remove(file_path)  # Remove local file after successful upload
    else:
        output_path = 'meetings.csv'  # Local path if AWS is not configured
        df.to_csv(output_path, index=False)
