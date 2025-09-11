import asyncio
import time

from aiobotocore.session import get_session


def lambda_handler(event, context):
    start = time.time()
    result = asyncio.run(processor(event))
    elapsed = round(time.time() - start, 1)

    return {
        "lang": "python",
        "detail": "aioboto3",
        "result": result,
        "time": elapsed,
    }


async def processor(event):
    session = get_session()  # This is comment
    async with session.create_client("s3") as s3:
        bucket_name = event["s3_bucket_name"]
        folder = event["folder"]
        find = event["find"]
        response = await s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
        keys = [obj["Key"] for obj in response["Contents"]]
        tasks = [get(s3, bucket_name, key, find) for key in keys]
        responses = await asyncio.gather(*tasks)
        if find is not None:
            first_non_none = next(value for value in responses if value is not None)
            return first_non_none
        else:
            return f"{len(responses)}"


async def get(s3, bucket_name: str, key: str, find: str) -> str or None:
    response = await s3.get_object(Bucket=bucket_name, Key=key)
    body = (await response["Body"].read()).decode("utf-8")
    if find is not None:
        return None if body.find(find) == -1 else key
    return None
