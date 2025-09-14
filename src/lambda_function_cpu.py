import os


def lambda_handler(event, context):
    """
    {
        "memory_size": 1024,
        "memory_size_increment" 128,
        "memory_size_max": 10240,
        "last_cpu_count": 2,
        "cpu_counts": {
            "128": 2
        }
    }
    """
    memory_size = event["memory_size"]
    last_cpu_count = event["last_cpu_count"] if "last_cpu_count" in event else 0
    cpu_counts = event["cpu_counts"] if "cpu_counts" in event else {}
    os_cpu_count = os.cpu_count()
    if os_cpu_count > last_cpu_count:
        last_cpu_count = os_cpu_count
        cpu_counts[memory_size] = os_cpu_count
    event["last_cpu_count"] = last_cpu_count
    event["cpu_counts"] = cpu_counts
    return event
