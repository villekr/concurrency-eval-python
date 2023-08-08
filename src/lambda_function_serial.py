import time
import boto3


def lambda_handler(event, context):
    start = time.time()
    result = processor(event)
    elapsed = round(time.time() - start, 1)

    return {
        "lang": "python",
        "detail": "boto3",
        "result": result,
        "time": elapsed,
    }


def processor(event):
    s3 = boto3.client("s3")
    bucket_name = event["s3_bucket_name"]
    folder = event["folder"]
    find = event["find"]
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder)
    keys = [obj["Key"] for obj in response["Contents"]]
    responses = [get(s3, bucket_name, key, find) for key in keys]
    if find:
        first_non_none = next(value for value in responses if value is not None)
        return first_non_none
    else:
        return f"{len(responses)}"


def get(s3, bucket_name: str, key: str, find: str) -> str or None:
    response = s3.get_object(Bucket=bucket_name, Key=key)
    body = response["Body"].read().decode("utf-8")
    if find is not None:
        return key if (body.find(find) != -1) else None
    return None
