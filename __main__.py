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
STACK = CONFIG.require_object("stack")
API = CONFIG.require_object("api")
BUS = CONFIG.require_object("bus")
LAMBDA = CONFIG.require_object("lambda")


# ----------------------------------------------------------------
# Automatically Inject Tags
# ----------------------------------------------------------------

register_auto_tags({
    "iac": "pulumi",
    'user:Project': pulumi.get_project(),
    'user:Stack': pulumi.get_stack(),
    "app-id": STACK.get("app_id"),
    "development-team-email": STACK.get("development_team_email"),
    "infrastructure-team-email": STACK.get("infrastructure_team_email"),
    "infrastructure-engineer-email": STACK.get("infrastructure_engineer_email"),
    "module": "pulumi-http-eventbridge-lambda",
    "module_source": "https://github.com/stephenbawks/pulumi-http-eventbridge-lambda"
})


# ----------------------------------------------------------------
# Create EventBridge Bus - Single Instance for Stack
# ----------------------------------------------------------------

bus_name = infra.create_event_bus(
    name="pizza-bus",
    archive_retention=BUS.get(
        "archive_retention"),
    enable_schema_discoverer=BUS.get(
        "schema_discoverer")
)

# ----------------------------------------------------------------
# Create HTTP API - Single Instance for Stack
# ----------------------------------------------------------------

infra.create_http_api(
    name="pizza-api",
    authorizer_type=API.get("authorizer_type"),
    authorizer_uri=API.get("authorizer_uri"),
    authorizer_audience=API.get("authorizer_audience"),
    bus_name=bus_name,
    api_url=API.get("url"),
    api_path=API.get("api_path"),
    route53_zone_name=API.get("route53_zone_name"),
    certificate_name=API.get("certificate_name"),
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
    function_name=LAMBDA.get("function_name"),
    runtime=LAMBDA.get("runtime"),
    code_source=LAMBDA.get("code_source"),
    handler=LAMBDA.get("handler"),
    memory=LAMBDA.get("memory"),
    queue_arn=new_pizza_queue,
    layer_arns=LAMBDA.get("layer_arns"),
    x_ray=LAMBDA.get("x_ray"),
    insights=LAMBDA.get("insights"),
    powertools=LAMBDA.get("powertools"),
)
