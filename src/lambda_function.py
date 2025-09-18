import asyncio
import os
import time
from typing import Optional, Union

from aioboto3 import Session
from botocore.config import Config

_SESSION = Session()
_S3_CONFIG = Config(max_pool_connections=os.getenv("MAX_POOL_CONNECTIONS", 512))


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
    async with _SESSION.client("s3", config=_S3_CONFIG) as s3:
        bucket_name = event["s3_bucket_name"]
        folder = event["folder"]
        find = event["find"]
        response = await s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
        keys = [obj["Key"] for obj in response.get("Contents", [])]

        tasks = [get(s3, bucket_name, key, find) for key in keys]
        responses = await asyncio.gather(*tasks)
        if find:
            first_non_none = next((value for value in responses if value is not None), None)
            return first_non_none
        else:
            return str(len(keys))


async def get(s3, bucket_name: str, key: str, find: Optional[Union[str, bytes]]) -> Optional[str]:
    response = await s3.get_object(Bucket=bucket_name, Key=key)
    body = await response["Body"].read()
    if find:
        return None if body.decode("utf-8").find(find) == -1 else key
    return None
