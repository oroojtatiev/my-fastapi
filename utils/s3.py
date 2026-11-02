"""
Quick script to verify AWS S3 credentials and permissions.

Run with:
  uv run python -m utils.s3 --check   # test upload/delete in the bucket
  uv run python -m utils.s3 --fill    # upload media/profile_pics/* to the bucket

--check runs check_s3_connection(): it uploads a small test object and deletes it,
so you can confirm your .env credentials work without going through the full
application flow.

--fill uploads every file from media/profile_pics into the bucket under the
profile_pics/ prefix (the same key layout the app uses for profile images).
"""

import argparse
import mimetypes
from io import BytesIO
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError

from config import settings
from utils.images import _get_s3_client

MEDIA_PROFILE_PICS_DIR = Path(__file__).resolve().parent.parent / "media" / "profile_pics"


def check_s3_connection():
  s3 = _get_s3_client()

  print(f"Bucket: {settings.s3_bucket_name}")
  print(f"Region: {settings.s3_region}")
  print()

  test_key = "profile_pics/test.txt"

  # Test upload
  try:
    s3.upload_fileobj(
      BytesIO(b"test"),
      settings.s3_bucket_name,
      test_key,
      ExtraArgs={"ContentType": "text/plain"},
    )
    print("Upload: SUCCESS")
  except (BotoCoreError, ClientError) as e:
    print(f"Upload: FAILED - {e}")
    return

  # Test delete
  try:
    s3.delete_object(Bucket=settings.s3_bucket_name, Key=test_key)
    print("Delete: SUCCESS")
  except (BotoCoreError, ClientError) as e:
    print(f"Delete: FAILED - {e}")
    return

  print()
  print("All tests passed! Your S3 configuration is working.")


def fill_s3():
  if not MEDIA_PROFILE_PICS_DIR.is_dir():
    print(f"Nothing to upload: {MEDIA_PROFILE_PICS_DIR} does not exist.")
    return

  s3 = _get_s3_client()

  print(f"Bucket: {settings.s3_bucket_name}")
  print(f"Source: {MEDIA_PROFILE_PICS_DIR}")
  print()

  files = sorted(p for p in MEDIA_PROFILE_PICS_DIR.iterdir() if p.is_file())

  if not files:
    print("Nothing to upload: the directory is empty.")
    return

  uploaded = 0

  for path in files:
    key = f"profile_pics/{path.name}"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    try:
      with path.open("rb") as f:
        s3.upload_fileobj(
          f,
          settings.s3_bucket_name,
          key,
          ExtraArgs={"ContentType": content_type},
        )
      uploaded += 1
      print(f"Upload: {path.name} -> {key} SUCCESS")
    except (BotoCoreError, ClientError) as e:
      print(f"Upload: {path.name} -> {key} FAILED - {e}")

  print()
  print(f"Done: {uploaded}/{len(files)} file(s) uploaded.")


def main():
  parser = argparse.ArgumentParser(
    description="Check S3 credentials or fill the bucket with local profile pictures."
  )
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument(
    "--check",
    action="store_true",
    help="run check_s3_connection(): test upload/delete in the bucket",
  )
  group.add_argument(
    "--fill",
    action="store_true",
    help="upload files from media/profile_pics to the bucket (profile_pics/ prefix)",
  )
  args = parser.parse_args()

  if args.check:
    check_s3_connection()
  else:
    fill_s3()


if __name__ == "__main__":
  main()
