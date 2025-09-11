# Concurrency Evaluation - Python
Python code for [How Do You Like Your Lambda Concurrency](https://ville-karkkainen.medium.com/how-do-you-like-your-aws-lambda-concurrency-part-1-introduction-7a3f7ecfe4b5)-blog series.

# Requirements
* Python 3.13
* uv

# CI/CD
This repo ships with a GitHub Actions workflow that:
- On pull requests: runs Ruff formatting and lint checks on the src/ folder.
- On pushes to the main branch: packages a Lambda layer (dependencies) and Lambda function code and uploads the zip files to an S3 artifact bucket. Authentication uses GitHub OIDC to assume an AWS IAM role.

## Required GitHub Actions configuration
To run the packaging and upload step on pushes to main, define the following repository-level Variables or Secrets in GitHub (Settings → Secrets and variables → Actions):

- ARTIFACT_BUCKET_NAME: Name of the S3 bucket where artifacts are uploaded.
- AWS_REGION: AWS region for the bucket and role (e.g., eu-north-1).
- WRITER_ROLE_ARN: ARN of the IAM role to assume via OIDC for uploading artifacts.

You may set these as Variables (recommended for non-sensitive values) or as Secrets. The workflow will read them from either Variables or Secrets and will fail early with a clear message if any is missing.

Example values (do not hard-code in workflow):
- ARTIFACT_BUCKET_NAME = 498781260522-eunorth1-concurrency-eval-infra-aws-main-artifacts
- AWS_REGION = eu-north-1
- WRITER_ROLE_ARN = arn:aws:iam::498781260522:role/concurrency-eval-main-artifact-writer

## AWS prerequisites
- Configure GitHub OIDC in your AWS account and trust the repository for the role above.
- The role assumed by the workflow needs permissions to upload to the artifact bucket, e.g. minimal S3 permissions:
  - s3:PutObject on s3://<artifact-bucket>/concurrency-eval-python/*
  - s3:PutObjectAcl if your bucket policy requires ACLs (often not needed)

## Outputs
The workflow exposes the following outputs from the packaging job (package-and-upload):
- s3_bucket: Name of the artifact S3 bucket.
- code_s3_key: S3 object key for the Lambda function zip without version info (e.g., concurrency-eval-python/lambda_function.zip).
- code_s3_version: Version identifier for the Lambda function S3 object.
- layer_s3_key: S3 object key for the Lambda layer zip without version info (e.g., concurrency-eval-python/lambda_layer.zip).
- layer_s3_version: Version identifier for the Lambda layer S3 object.

These outputs can be consumed by subsequent jobs or reusable workflows via job outputs. The job summary will also display the resolved values.

Note: The bucket should have S3 Versioning enabled. We rely on S3 object versions instead of embedding project version numbers or timestamps in paths.
