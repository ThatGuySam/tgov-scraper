import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

def is_aws_configured():
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    return all(var in os.environ for var in required_vars)


def create_bucket_if_not_exists(bucket_name):
    s3 = boto3.client('s3')
    
    try:
        # Check if the bucket exists by listing its objects
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # Bucket does not exist, create it
            try:
                s3.create_bucket(Bucket=bucket_name)
                print(f"Bucket '{bucket_name}' created.")
            except ClientError as error:
                print(f"Failed to create bucket '{bucket_name}': {error}")
        else:
            # Handle other ClientError exceptions
            print(f"Client error: {e}")


def upload_to_s3(file_path, bucket_name, s3_path):
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, bucket_name, s3_path)
        print(f"Uploaded {file_path} to {bucket_name}/{s3_path}")
        return True
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Failed to upload to S3: {str(e)}")
        return False

