import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from os import getenv
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = getenv("MINIO_SECRET_KEY")
MINIO_BUCKET_NAME = getenv("MINIO_BUCKET_NAME")

MINIO_EXTERNAL_ENDPOINT = getenv("MINIO_EXTERNAL_ENDPOINT")


def get_s3_client(external=False):
    endpoint = MINIO_EXTERNAL_ENDPOINT if external else MINIO_ENDPOINT
    return boto3.client(
        "s3",
        endpoint_url=f"http://{endpoint}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",  # minio requires a region
    )


def create_presigned_url(object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object for external access."""
    s3_client = get_s3_client(external=True)
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": MINIO_BUCKET_NAME, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None
    return response


def delete_object(object_name):
    """Delete an object from an S3 bucket."""
    s3_client = get_s3_client()
    try:
        s3_client.delete_object(Bucket=MINIO_BUCKET_NAME, Key=object_name)
    except ClientError as e:
        print(f"Error deleting object: {e}")
        return False
    return True
