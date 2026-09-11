import os
import sys
import datetime
from urllib.parse import urlparse

# CloudFront Configuration — read from environment variables
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN", "https://d30beya68etkmf.cloudfront.net")
CLOUDFRONT_KEY_PAIR_ID = os.getenv("CLOUDFRONT_KEY_PAIR_ID", "")
CLOUDFRONT_PRIVATE_KEY = os.getenv("CLOUDFRONT_PRIVATE_KEY", "")  # PEM string
CLOUDFRONT_URL_EXPIRY_DAYS = int(os.getenv("CLOUDFRONT_URL_EXPIRY_DAYS", "30"))


def generate_cloudfront_url(s3_url: str) -> str:
    """
    Convert an S3 URL into the corresponding CloudFront URL.
    
    If CLOUDFRONT_KEY_PAIR_ID and CLOUDFRONT_PRIVATE_KEY are configured,
    generates a signed CloudFront URL with 30-day expiry.
    Otherwise, generates an unsigned CloudFront URL (permanent).

    Example (unsigned):
        https://resolve-x-production.s3.ap-south-1.amazonaws.com/cpass/foo.wav
        → https://d30beya68etkmf.cloudfront.net/cpass/foo.wav

    Example (signed, 30-day):
        https://d30beya68etkmf.cloudfront.net/cpass/foo.wav?Policy=...&Signature=...&Key-Pair-Id=...
    """
    parsed = urlparse(s3_url)
    object_key = parsed.path.lstrip("/")
    base_url = f"{CLOUDFRONT_DOMAIN}/{object_key}"

    # If signing credentials are available, produce a signed URL with expiry
    if CLOUDFRONT_KEY_PAIR_ID and CLOUDFRONT_PRIVATE_KEY:
        return _generate_signed_cloudfront_url(base_url)

    return base_url


_cf_signer = None


def _get_cf_signer():
    global _cf_signer
    if _cf_signer is None and CLOUDFRONT_KEY_PAIR_ID and CLOUDFRONT_PRIVATE_KEY:
        from botocore.signers import CloudFrontSigner
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

        private_key_pem = CLOUDFRONT_PRIVATE_KEY
        if "\\n" in private_key_pem:
            private_key_pem = private_key_pem.replace("\\n", "\n")

        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None
        )

        def rsa_signer(message: bytes) -> bytes:
            return private_key.sign(message, asym_padding.PKCS1v15(), hashes.SHA1())  # noqa: S303

        _cf_signer = CloudFrontSigner(CLOUDFRONT_KEY_PAIR_ID, rsa_signer)
    return _cf_signer


def _generate_signed_cloudfront_url(url: str) -> str:
    """Generate a signed CloudFront URL using botocore CloudFrontSigner."""
    signer = _get_cf_signer()
    if not signer:
        return url

    expire_date = datetime.datetime.utcnow() + datetime.timedelta(days=CLOUDFRONT_URL_EXPIRY_DAYS)
    return signer.generate_presigned_url(url, date_less_than=expire_date)


if __name__ == "__main__":
    url_to_process = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://resolve-x-production.s3.ap-south-1.amazonaws.com/"
             "cpass/abhiyan/public/s-bot-recordings/sample.wav"
    )

    cloudfront_url = generate_cloudfront_url(url_to_process)

    print("CloudFront URL:")
    print(cloudfront_url)
