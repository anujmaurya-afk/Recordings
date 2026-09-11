import os
import sys
from urllib.parse import urlparse
import boto3
from botocore.config import Config

# AWS Configuration — read from environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
REGION_NAME = os.getenv("AWS_REGION", "ap-south-1")

# AWS S3 Maximum Expiration (7 Days)
EXPIRATION_IN_SECONDS = int(os.getenv("RECORDING_URL_EXPIRY_SECONDS", "604800"))


# Global cached S3 client for high-throughput presigning
_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=REGION_NAME,
            config=Config(signature_version="s3v4"),
        )
    return _s3_client


def parse_s3_url(url: str):
    """Extracts bucket name and object key from standard S3 HTTPS URLs or s3:// URIs."""
    if url.startswith("s3://"):
        parsed = urlparse(url)
        return parsed.netloc, parsed.path.lstrip("/")

    parsed = urlparse(url)
    bucket_name = parsed.netloc.split(".")[0]
    object_key = parsed.path.lstrip("/")
    return bucket_name, object_key


def generate_presigned_url(s3_url: str) -> str:
    bucket, key = parse_s3_url(s3_url)
    client = get_s3_client()

    presigned_url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=EXPIRATION_IN_SECONDS,
    )
    return presigned_url


if __name__ == "__main__":
    url_to_process = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://resolve-x-production.s3.ap-south-1.amazonaws.com/cpass/abhiyan/public/s-bot-recordings/sample.wav"
    )
    presigned = generate_presigned_url(url_to_process)
    print("Generated Presigned URL (Valid for 7 days):")
    print(presigned)
