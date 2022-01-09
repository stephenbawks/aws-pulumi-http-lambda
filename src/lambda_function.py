import os
import json
from aws_lambda_powertools import Tracer, Logger, Metrics
from aws_lambda_powertools.utilities.data_classes import event_source, EventBridgeEvent
from aws_lambda_powertools.utilities import parameters




# Grabbing Environmental Variables on the Lambda Function
# https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-retrieve
REGION = os.environ['AWS_REGION']
ENVIRONMENT = os.environ['ENVIRONMENT']
APP_ID = os.environ['APP_ID']
BUCKET_NAME = os.environ['BUCKET_NAME']

###############################################################################
#                     Documentation for the Lambda Function                   #
###############################################################################
# Inside Lambda - What is inside AWS lambda? Are there things inside there? Let's find out!
# https://insidelambda.com/

# Create boto3 Events Client
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/events.html
# events = boto3.client('events')

# Lambda Defined/Reserverd runtime environment variables
# https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-runtime

# Lambda Context - Python
# https://docs.aws.amazon.com/lambda/latest/dg/python-context.html

# Lambda HTTP API Payload
# https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html

# Amazon EventBridge Events
# https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-events.html

###############################################################################


# Tracer and Logger are part of AWS Lambda Powertools Python
# https://awslabs.github.io/aws-lambda-powertools-python/latest/
tracer = Tracer()  # Sets service via env var
logger = Logger()
metrics = Metrics()


@tracer.capture_method(capture_response=False)
def extract_data(event: dict):
    #Extract the body from event
    if 'body' in event:
        data = event['body']
        try:
            data = json.loads(data)
            return data
        except ValueError as e:
            return False


@app.get("/event")
@tracer.capture_method
def post_event(event: dict, context: dict) -> dict:
    """
    Function that exists to pull back a specfic company that is being
    searched for from the IPs from rock-foc-ips.json file

    Parameters:
        company_name (str): Company name to search for

    Returns:
        output (dict): Returns company info from rock-foc-ips.json file
    """
    event_body = event['body']


    return output



@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def lambda_handler(event, context):

    #Extract the body from event
    event_data = extract_data(event)
    if event_data is False:
        response = {"statusCode": 400, "message": "Invalid JSON in body"}
        return json.dumps(response)


    correlation_id = event["requestContext"]["requestId"]
    originating_ip = event['headers']['x-forwarded-for']

    logger.append_keys(source_ip=originating_ip)
    logger.append_keys(lambda_request_id=context.aws_request_id)
    logger.set_correlation_id(correlation_id)

    return app.resolve(event, context)

