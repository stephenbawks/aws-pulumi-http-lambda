"""An AWS Python Pulumi program"""

# pylint: disable=line-too-long,invalid-name

import json
import pulumi
# import pulumi_aws as aws
from autotag import register_auto_tags
import infra


# ----------------------------------------------------------------
# Pull Stack Variables from Config File
# ----------------------------------------------------------------
CONFIG = pulumi.Config()

# ----------------------------------------------------------------
# Automatically Inject Tags
# ----------------------------------------------------------------

register_auto_tags({
    "iac": "pulumi",
    'user:Project': pulumi.get_project(),
    'user:Stack': pulumi.get_stack(),
    "app-id": 123456,
    "development-team-email": "email@example.com",
    "infrastructure-team-email": "email@example.com",
    "infrastructure-engineer-email": "email@example.com",
    "module": "pulumi-http-eventbridge-lambda",
    "module_source": "https://github.com/stephenbawks/pulumi-http-eventbridge-lambda"
})


# ----------------------------------------------------------------
# Create EventBridge Bus - Single Instance for Stack
# ----------------------------------------------------------------

bus_name = infra.create_event_bus(
    name="pizza-bus",
    archive_retention=7,
    enable_schema_discoverer=True,
)

# ----------------------------------------------------------------
# Create HTTP API - Single Instance for Stack
# ----------------------------------------------------------------

infra.create_http_api(
    name="pizza-api",
    authorizer_type="JWT",
    authorizer_uri=CONFIG.get('api_authorizer_uri'),
    authorizer_audience=CONFIG.get('authorizer_audience'),
    bus_name=bus_name,
    api_url=CONFIG.get('api_url'),
    api_path="POST /event",
    route53_zone_name=CONFIG.get('route53_zone_name'),
    certificate_name=CONFIG.get('certificate_name'),
)

# ----------------------------------------------------------------
# SQS - Single or Mulitple Instances for Stack
# ----------------------------------------------------------------

new_pizza_queue = infra.create_sqs_queue(name="NewPizza")
cancel_pizza_queue = infra.create_sqs_queue(name="CancelPizza")

# ----------------------------------------------------------------
# EventBridge Rules/Targets - Single or Mulitple Instances for Stack
# ----------------------------------------------------------------

new_pizza_pattern = json.dumps({
    "source": ["pizza.pineapple.events"],
    "detail": {
        "source": ["Pizza"],
        "detail-type": ["NewOrder"]
    }
})
new_pizza_rule = infra.create_rule_and_sqs_target(
    name="NewPizza", bus_name=bus_name, rule_pattern=new_pizza_pattern, queue_target_arn=new_pizza_queue)

cancel_pizza_pattern = json.dumps({
    "source": ["pizza.pineapple.events"],
    "detail": {
        "source": ["Pizza"],
        "detail-type": ["CancelOrder"]
    }
})
cancel_pizza_rule = infra.create_rule_and_sqs_target(
    name="CancelPizza", bus_name=bus_name, rule_pattern=cancel_pizza_pattern, queue_target_arn=cancel_pizza_queue)

# ----------------------------------------------------------------
# Lambda - Single or Mulitple Instances for Stack
# ----------------------------------------------------------------

infra.create_lambda_function(
    function_name="doStuff",
    runtime="python3.9",
    code_source="./src",
    handler="lambda_function.lambda_handler",
    memory=CONFIG.get_int('lambda_memory'),
    queue_arn=new_pizza_queue,
    # layer_arns=LAMBDA.get("layer_arns"),
    x_ray=True,
    insights=True,
    powertools=True,
)
