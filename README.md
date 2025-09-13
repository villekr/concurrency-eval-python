# Concurrency Evaluation - Python
Python code for [How Do You Like Your Lambda Concurrency](https://ville-karkkainen.medium.com/how-do-you-like-your-aws-lambda-concurrency-part-1-introduction-7a3f7ecfe4b5)-blog series.

# Requirements
* Python 3.13
* uv

Target is to implement the following pseudocode as effectively as possible using language-specific idioms and constrains to achieve concurrency.
Mandatory requirements:
- Code must contain at least the following three functions: handler, processor and get
- The processor-function must be encapsulated with timing functions
- Each S3 objects' body must be fully read
- If find-string is specified, the key of the first s3 object that contains the string must be returned
- Code must each return the number of s3 objects listed or the key of the first s3 object that contains the string
```
# Idiomatic language specific AWS Lambda handler
func handler(event):
    timer.start()
    result = processor(event)
    timer.stop()
    return {
        "time": timer.elapsed,
        "result": result
    }
    
# Concurrently list and get objects from S3 bucket
func processor(event):
    s3_objects = aws_sdk.list_objects(s3_bucket)
    results = [get(s3_key, event[find]) for s3_objects]
    return first_non_none(results) if event[find] else len(s3_objects)

# Get single object's body from S3, try to find a string if specified
func get(s3_key, find):
    body = aws_sdk.get_object(s3_key).body
    return body.find(find) if find else None
```