import os

from lambda_function_serial import lambda_handler

if __name__ == "__main__":
    response = lambda_handler(
        {
            "s3_bucket_name": os.getenv("S3_BUCKET_NAME"),
            "folder": os.getenv("FOLDER"),
            "find": None,
        },
        None,
    )
    print(response)
    response = lambda_handler(
        {
            "s3_bucket_name": os.getenv("S3_BUCKET_NAME"),
            "folder": os.getenv("FOLDER"),
            "find": os.getenv("FIND"),
        },
        None,
    )
    print(response)
