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
  - s3:PutObject on s3://<artifact-bucket>/concurrency-eval-python/lambda_layer/* and s3://<artifact-bucket>/concurrency-eval-python/lambda_function/*
  - s3:PutObjectAcl if your bucket policy requires ACLs (often not needed)

## Outputs
When the push workflow completes, it prints S3 URIs for:
- Lambda layer zip under s3://<artifact-bucket>/concurrency-eval-python/lambda_layer/<version>/<yyyymmdd>/<shortsha>.zip
- Lambda function zip under s3://<artifact-bucket>/concurrency-eval-python/lambda_function/<version>/<yyyymmdd>/<shortsha>.zip
