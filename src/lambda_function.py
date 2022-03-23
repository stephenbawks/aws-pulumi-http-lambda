import os
import json
import urllib3
import jwt
from datetime import datetime
from loguru import logger as logs
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools import Tracer, Logger, Metrics
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent
from aws_lambda_powertools.utilities import parameters


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
metrics = Metrics(namespace="RHDSEvents", service="Serparation")


@tracer.capture_method
def lookup_auth0_user(user_details: dict) -> dict:
    """_summary_

    Args:
        user_details (dict): _description_

    Returns:
        dict: _description_
    """

    auth0_results = []

    email_address = user_details["email_address"]
    common_id = user_details["common_id"]
    rock_human_id = user_details["rock_human_id"]

    auth0_environments = ["test", "beta", "prod"]
    for env in auth0_environments:
        logs.info(f"Checking Auth0 Token - Evnironment {env}")
        auth0_token_path = f"/tmp/auth0_{env}_token.txt"
        if os.path.isfile(auth0_token_path):
            logs.info("Auth0 Token Exists - Importing and Check Expiration")
            file = open(auth0_token_path, 'r')
            auth0_token = file.read()
            file.close()
            if check_token_expires(auth0_token):
                logs.info("Auth0 Token is still Valid")
            else:
                logs.info("Auth0 Token will expire soon - Requesting New Token")
                auth0_token = get_auth0_token(environment=env)
                file = open(f"/tmp/auth0_{env}_token.txt", "w")
                file.write(auth0_token)
                file.close()
        else:
            logs.info("Auth0 Token Does Not Exist - Getting New Token")
            auth0_token = get_auth0_token(environment=env)
            file = open(f"/tmp/auth0_{env}_token.txt", "w")
            file.write(auth0_token)
            file.close()

        if env == "test":
            host_address = "sso-test.rock-dev.auth0.com"
        elif env == "beta":
            host_address = "sso-beta.rock-dev.auth0.com"
        elif env == "prod":
            host_address = "sso.rock.auth0.com"

        http = urllib3.PoolManager()
        auth0_response = http.request(
            "GET",
            f"https://{host_address}/api/v2/users?q=app_metadata.commonid:%22{common_id}%22 OR app_metadata.rock_human_id:%22{rock_human_id}%22&search_engine=v3",
            headers={"Authorization": f"Bearer {auth0_token}",
                     "Content-Type": "application/json"}
        )
        # decode bytes to string and then load json
        json_response = json.loads(auth0_response.data.decode())
        # get the Auth0 User ID
        auth0_user_id = json_response[0]['user_id']

        if len(auth0_response.data.decode()) == 2:
            logs.info(
                f"The email address was not found in Auth0 Environment: {env}")
        else:
            logs.info(
                f"Attempting block TM - CommonID {common_id} or RHID: {rock_human_id} in Auth0 Environment: {env}")
            # Block Auth0 User's Auth0 ID
            auth0_block = http.request(
                "GET",
                f"https://{host_address}/api/v2/user?identifier={auth0_user_id}",
                headers={"Authorization": f"Bearer {auth0_token}",
                         "Content-Type": "application/json"}
            )

            status = auth0_block.status
            if status == 200:
                json_auth0_block = json.loads(auth0_block.data.decode())
                blocked_result = json_auth0_block['blocked']
                auth0_results.append({"environment": env, "auth0_id": auth0_user_id,
                                      "email_address": email_address, "blocked_status": blocked_result})
            elif status == 404:
                auth0_results.append({"environment": env, "auth0_id": None,
                                      "email_address": email_address, "blocked_status": False})

    return auth0_results


@tracer.capture_method
def lookup_rhid(rhid: str, access_token: str) -> str:
    """
    Looks up a RHID in the RHD GraphQL API

    Args:
        rhid (str): A RHID
        access_token (str): A JWT token

    Returns:
        str: Email address of the RHID Team Member
    """
    query = """{teamMember (where: {rockHumanId: "%s"}) {
        preferredFirstName
        preferredLastName
        rockHumanId
        commonId
        teamMemberJobs (where: {isPrimary:true}) {
            businessArea
            displayJobTitle
            email
        }
        }
    }""" % (rhid)

    data = {"query": query}
    json_data = json.dumps(data)
    header = {"Authorization": f"Bearer {access_token}",
              "Content-Type": "application/json"}

    http = urllib3.PoolManager()
    r = http.request(
        "POST",
        "https://graphql.tmds.foc.zone/",
        body=json_data,
        headers=header
    )
    data = json.loads(r.data.decode())
    email_address = data['data']['teamMember']['teamMemberJobs'][0]['email']
    common_id = data['data']['teamMember']['teamMemberJobs'][0]['commonId']
    rock_human_id = data['data']['teamMember']['teamMemberJobs'][0]['rockHumanId']

    # return email_address
    return {"email_address": email_address, "common_id": common_id, "rock_human_id": rock_human_id}


@tracer.capture_method
def get_rhds_token() -> str:
    """
    Get the RHDS Token from the Environment Variables

    Args:

    Returns:
        str: The RHDS Access Token
    """
    # rhds_address = "graphql.tmds.foc.zone"
    rhds_provider = parameters.SSMProvider()
    rhds_address = rhds_provider.get("/rhds-events/rhds-api/url", decrypt=True)
    rhds_audience = rhds_provider.get(
        "/rhds-events/rhds-api/audience", decrypt=True)
    rhds_client_id = rhds_provider.get(
        "/rhds-events/rhds-api/client_id", decrypt=True)
    rhds_client_secret = rhds_provider.get(
        "/rhds-events/rhds-api/client_secret", decrypt=True)

    body = {
        'grant_type': 'client_credentials',
        'audience': rhds_audience,
        'client_id': rhds_client_id,
        'client_secret': rhds_client_secret
    }
    encoded_data = json.dumps(body)

    http = urllib3.PoolManager()
    rhds_response = http.request(
        "POST",
        f"https://{rhds_address}/oauth/token",
        body=encoded_data,
        headers={"Content-Type": "application/json"}
    )

    # decode bytes to string and then load json
    data = json.loads(rhds_response.data.decode())
    header = rhds_response.headers

    access_token = data["access_token"]

    return access_token


@tracer.capture_method
def get_auth0_token(environment: str):
    """
    Gets an Auth0 token for the specified environment

    Args:
        environment (str): The environment to get the token for

    URLs:
        https://github.com/auth0/auth0-python

    """
    if environment == "test":
        auth0_client_domain = "sso-test.rock-dev.auth0.com"
        auth0_audience = "https://sso-test.rock-dev.auth0.com/api/v2/"
    elif environment == "beta":
        auth0_client_domain = "sso-beta.rock-dev.auth0.com"
        auth0_audience = "https://sso-beta.rock-dev.auth0.com/api/v2/"
    elif environment == "prod":
        auth0_client_domain = "sso.rock.auth0.com"
        auth0_audience = "https://sso.rock.auth0.com/api/v2/"

    auth0_provider = parameters.SSMProvider()
    auth0_client_id = auth0_provider.get(
        f"/rhds-events/auth0/{environment}/client_id", decrypt=True)
    auth0_client_secret = auth0_provider.get(
        f"/rhds-events/auth0/{environment}/client_secret", decrypt=True)

    get_token = GetToken(auth0_client_domain)
    token = get_token.client_credentials(
        auth0_client_id, auth0_client_secret, f"https://{auth0_client_domain}/api/v2/")
    mgmt_api_token = token["access_token"]

    return mgmt_api_token


@tracer.capture_method
def check_token_expires(token: str) -> bool:
    """
    Checks to see if the token is close to expiring

    Args:
        token (str): A JWT token

    Returns:
        bool: True/False
    """
    print("Function: check_token_expires")

    expires = jwt.decode(token, options={"verify_signature": False})["exp"]
    expires_date = datetime.fromtimestamp(expires)
    now = datetime.now()
    seconds_exp = (expires_date - now).total_seconds()
    print(f"Expires Seconds: {seconds_exp}")
    if seconds_exp < 45:
        print("Token Expiration less than 45 seconds, getting new one.")
        return False
    else:
        return True


@tracer.capture_method
def so_many_events(record: str, rhid_access_token: str):
    """
    This function is called when an event is received by the Lambda function.

    Args:
        record (str): The event that was received.

    Returns:
        str: The response to send back to the event source.
    """

    auth0_results = []

    print("Function: so_many_events")
    record = json.loads(record)
    detail = record["detail"]["detail"]
    company_id = detail["companyId"]
    print(f"Company ID: {company_id}")
    for impacted in detail["impacted"]:
        entity_id = impacted["entityId"]
        print(f"Entity ID: {entity_id}")
        rock_human_id = impacted["rockHumanId"]
        print(f"Rock Human ID: {rock_human_id}")
        event_type = impacted["eventType"]
        print(f"Event Type: {event_type}")

        # Query RHDS with Rock Human ID to get email
        team_memeber_object = lookup_rhid(
            rhid=rock_human_id, access_token=rhid_access_token)

        lookup_results = lookup_auth0_user(user_details=team_memeber_object)
        logs.info(lookup_results)
        auth0_results.append(lookup_results)

    return auth0_results


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@event_source(data_class=SQSEvent)
def lambda_handler(event: SQSEvent, context):
    """
    This function is called when an event is received by the Lambda function.
    """
    rhds_token_path = "/tmp/rhds_token.txt"

    if os.path.isfile(rhds_token_path):
        logs.info("RHDS Token Exists - Importing and Check Expiration")
        file = open(rhds_token_path, 'r')
        token = file.read()
        file.close()
        if check_token_expires(token):
            rhds_token = get_rhds_token()
            file = open(rhds_token_path, "w")
            file.write(rhds_token)
            file.close()
    else:
        logs.info("RHDS Token Does Not Exist - Getting New Token")
        rhds_token = get_rhds_token()
        file = open(rhds_token_path, "w")
        file.write(rhds_token)
        file.close()

    # Multiple records can be delivered in a single event
    for record in event.records:
        # print("Ouput SQS Record")
        # print(record.body)
        so_many_events(record=record.body, rhid_access_token=rhds_token)

    correlation_id = event["requestContext"]["requestId"]
    originating_ip = event['headers']['x-forwarded-for']

    logger.append_keys(source_ip=originating_ip)
    logger.append_keys(lambda_request_id=context.aws_request_id)
    logger.set_correlation_id(correlation_id)
