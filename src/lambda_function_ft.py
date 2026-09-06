import time

import boto3
import tonio
from botocore.config import Config

# Reuse a single boto3 client across invocations. botocore clients are
# thread-safe for calls, which matters here because TonIO dispatches the
# blocking S3 calls onto real threads running in parallel (GIL disabled).
_S3 = boto3.client("s3", config=Config(max_pool_connections=50))

# TonIO's run()/main() may only be called once per program, so we create a
# long-lived runtime and reuse it across warm Lambda invocations.
_RUNTIME = tonio.runtime()


def lambda_handler(event, context):
    start = time.perf_counter()
    result = _RUNTIME.run_until_complete(processor(event))
    elapsed = round(time.perf_counter() - start, 1)

    return {
        "lang": "python",
        "detail": "tonio",
        "result": result,
        "time": elapsed,
    }


def processor(event):
    bucket_name = event["s3_bucket_name"]
    folder = event["folder"]
    find = event["find"]

    response = _S3.list_objects_v2(Bucket=bucket_name, Prefix=folder, MaxKeys=1000)
    keys = [obj["Key"] for obj in response.get("Contents", [])]

    # Each get() runs boto3 (blocking) on TonIO's blocking thread-pool, so all
    # object reads proceed in parallel across free threads.
    responses = yield tonio.spawn(*[get(bucket_name, key, find) for key in keys])
    if find:
        return next((value for value in responses if value is not None), None)
    else:
        return f"{len(keys)}"


def get(bucket_name: str, key: str, find: str):
    body = yield tonio.spawn_blocking(_read_object, bucket_name, key)
    if find:
        return key if (body.find(find) != -1) else None
    return None


def _read_object(bucket_name: str, key: str) -> str:
    response = _S3.get_object(Bucket=bucket_name, Key=key)
    return response["Body"].read().decode("utf-8")
