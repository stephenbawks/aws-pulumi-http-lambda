import os
# from loguru import logger as logs
# from aws_lambda_powertools.metrics import MetricUnit
# from aws_lambda_powertools import Tracer, Logger, Metrics
# from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent
# from aws_lambda_powertools.utilities import parameters


# Grabbing Environmental Variables on the Lambda Function
# https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-retrieve
REGION = os.environ['AWS_REGION']

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
metrics = Metrics(namespace="PineapplePizza", service="Magic")




@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@event_source(data_class=SQSEvent)
def lambda_handler(event: SQSEvent, context):
    """
    This function is called when an event is received by the Lambda function.
    """

    correlation_id = event["requestContext"]["requestId"]
    originating_ip = event['headers']['x-forwarded-for']

    logger.append_keys(source_ip=originating_ip)
    logger.append_keys(lambda_request_id=context.aws_request_id)
    logger.set_correlation_id(correlation_id)

    # dosomething here
