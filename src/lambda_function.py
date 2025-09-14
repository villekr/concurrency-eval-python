import asyncio
import time
from typing import Optional, Union

from aioboto3 import Session
from botocore.config import Config

# Reuse the aioboto3 session between Lambda invocations to reduce overhead
_SESSION = Session()
# Increase connection pool size to improve throughput with concurrent S3 requests
_S3_CONFIG = Config(max_pool_connections=256)


def lambda_handler(event, context):
    start = time.perf_counter()
    result = asyncio.run(processor(event))
    elapsed = round(time.perf_counter() - start, 1)

    return {
        "lang": "python",
        "detail": "aioboto3",
        "result": result,
        "time": elapsed,
    }


async def processor(event):
    # Optional concurrency limit to avoid connection thrashing; defaults to a sensible value
    max_concurrency = int(event.get("concurrency", 64))
    sem = asyncio.Semaphore(max_concurrency)

    async with _SESSION.client("s3", config=_S3_CONFIG) as s3:
        bucket_name = event["s3_bucket_name"]
        folder = event["folder"]
        find = event["find"]
        response = await s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
        keys = [obj["Key"] for obj in response.get("Contents", [])]

        tasks = [get(s3, bucket_name, key, find, sem) for key in keys]
        responses = await asyncio.gather(*tasks)
        if find:
            # Return the first key that matched (order preserved by gather)
            first_non_none = next((value for value in responses if value is not None), None)
            return first_non_none
        else:
            return str(len(keys))


async def get(
    s3, bucket_name: str, key: str, find: Optional[Union[str, bytes]], sem: asyncio.Semaphore
) -> Optional[str]:
    async with sem:
        response = await s3.get_object(Bucket=bucket_name, Key=key)
        body_bytes = await response["Body"].read()  # fully read the body as required
        if find:
            # Compare in bytes to avoid an unnecessary UTF-8 decode for large objects
            if isinstance(find, str):
                find_bytes = find.encode("utf-8")
            else:
                # find is bytes here
                find_bytes = find
            return key if body_bytes.find(find_bytes) != -1 else None
        return None
