import os
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

# On AWS Lambda vCPU scales with memory (a full vCPU only around ~1769 MB), so a
# free-threaded runtime is CPU-starved at low memory tiers. Spawning all reads
# at once then thrashes the blocking thread-pool and the connection pool.
# Cap the number of in-flight reads to roughly match the available vCPU budget
# derived from the configured memory, which lets each read make steady progress
# at low tiers while staying fully parallel at high tiers.
_MEMORY_MB = int(os.environ.get("AWS_LAMBDA_FUNCTION_MEMORY_SIZE", "1024"))
# ~1 in-flight read per ~32 MB, clamped to a sane [8, 64] range. This keeps the
# batch small (and CPU contention low) at 256 MB while opening up at 1024 MB+.
_MAX_INFLIGHT = max(8, min(64, _MEMORY_MB // 32))


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

    # Search on raw bytes to avoid a per-object UTF-8 decode, which is pure CPU
    # work that dominates at low-memory (low-vCPU) tiers. The body is still read
    # in full below; only the wasteful decode is skipped.
    find_bytes = find.encode("utf-8") if find else None

    response = _S3.list_objects_v2(Bucket=bucket_name, Prefix=folder, MaxKeys=1000)
    keys = [obj["Key"] for obj in response.get("Contents", [])]

    # Each get() runs boto3 (blocking) on TonIO's blocking thread-pool, so reads
    # proceed in parallel across free threads. Concurrency is bounded to
    # _MAX_INFLIGHT so low-vCPU tiers are not overwhelmed; higher tiers still
    # saturate their cores. Every object is still read in full (all batches are
    # processed), matching the required semantics; only the in-flight count is
    # capped.
    first_match = None
    for i in range(0, len(keys), _MAX_INFLIGHT):
        batch = keys[i : i + _MAX_INFLIGHT]
        responses = yield tonio.spawn(*[get(bucket_name, key, find_bytes) for key in batch])
        if find_bytes and first_match is None:
            first_match = next((value for value in responses if value is not None), None)

    if find_bytes:
        return first_match
    return f"{len(keys)}"


def get(bucket_name: str, key: str, find: bytes | None):
    body = yield tonio.spawn_blocking(_read_object, bucket_name, key)
    if find:
        return key if (body.find(find) != -1) else None
    return None


def _read_object(bucket_name: str, key: str) -> bytes:
    response = _S3.get_object(Bucket=bucket_name, Key=key)
    # Fully read the object body (required); keep it as bytes to avoid decoding.
    return response["Body"].read()
