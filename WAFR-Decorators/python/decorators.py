import functools
import json
from botocore.exceptions import ClientError

def catch_errors(handler):
    """
    Decorator which performs catch all exception handling
    """

    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except ClientError as e:
            return {
                "statusCode": e.response["ResponseMetadata"].get("HTTPStatusCode", 400),
                "body": json.dumps({"Message": "Client error: {}".format(str(e)),}),
            }
        except ValueError as e:
            return {
                "statusCode": 400,
                "body": json.dumps({"Message": "Invalid request: {}".format(str(e)),}),
            }
        except Exception as e:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"Message": "Unable to process request: {}".format(str(e)),}
                ),
            }

    return wrapper
