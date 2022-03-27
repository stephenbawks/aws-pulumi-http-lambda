"""_summary_

Returns:
    _type_: _description_
"""
# pylint: disable=line-too-long,invalid-name,too-many-arguments,too-many-locals

from typing import Optional
import sys
import pulumi
import pulumi_aws as aws


conf = pulumi.Config()
AWS_ACCOUNT_ID = (aws.get_caller_identity()).account_id
AWS_REGION = (aws.get_region()).name

ENVIRONMENT = pulumi.get_stack()
APP_NAME = pulumi.get_project()
STACK_NAME = f"{ENVIRONMENT}-{APP_NAME}"

INSIGHTS_LAYER_X86 = f"arn:aws:lambda:{AWS_REGION}:580247275435:layer:LambdaInsightsExtension:18"
INSIGHTS_LAYER_ARM64 = f"arn:aws:lambda:{AWS_REGION}:580247275435:layer:LambdaInsightsExtension-Arm64:2"
POWERTOOLS_LAYER = f"arn:aws:lambda:{AWS_REGION}:017000801446:layer:AWSLambdaPowertoolsPython:15"


# ----------------------------------------------------------------
# EventBridge Event Bus
# ----------------------------------------------------------------

def create_event_bus(name: str, archive_retention: Optional[int] = 7, enable_schema_discoverer: Optional[bool] = False) -> str:
    """
    Creates an EventBridge Event Bus

    Args:
        resource_name (str): A name that will be used to create the EventBridge Event Bus

    Returns:
        str: EventBridge Event Bus ARN
    """

    # https://www.pulumi.com/registry/packages/aws/api-docs/cloudwatch/eventbus/
    event_bus = aws.cloudwatch.EventBus(
        f"{name}EventBus",
        name=f"{STACK_NAME}-bus",
    )

    # https: // www.pulumi.com/registry/packages/aws/api-docs/cloudwatch/eventarchive/
    event_archive = aws.cloudwatch.EventArchive(
        f"{name}EventArchive",
        name=f"archive-{STACK_NAME}",
        event_source_arn=event_bus.arn,
        retention_days=archive_retention,
        opts=pulumi.ResourceOptions(
            parent=event_bus)
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/schemas/discoverer/
    if enable_schema_discoverer:
        schema_discoverer = aws.schemas.Discoverer(
            "eventBusSchemaDiscoverer",
            source_arn=event_bus.arn,
            description="Auto discover event schemas",
            opts=pulumi.ResourceOptions(
                parent=event_bus)
        )
        pulumi.export("SchemaDiscoverer", schema_discoverer.arn)

    api_assume_role = aws.iam.get_policy_document(statements=[aws.iam.GetPolicyDocumentStatementArgs(
        actions=["sts:AssumeRole"],
        principals=[aws.iam.GetPolicyDocumentStatementPrincipalArgs(
            type="Service",
            identifiers=["apigateway.amazonaws.com"]
        )],
    )])

    bus_policy = aws.iam.get_policy_document(statements=[
        aws.iam.GetPolicyDocumentStatementArgs(
            sid="HttpApiToEventbridge",
            actions=[
                "events:PutEvents"
            ],
            resources=[
                event_bus.arn
            ],
        )]
    )

    bus_managed_policy = aws.iam.Policy(
        f"{name}HttpToEventbridge",
        path="/",
        policy=bus_policy.json,
        opts=pulumi.ResourceOptions(
            parent=event_bus)
    )

    aws.iam.Role(
        "apiBusRole",
        assume_role_policy=api_assume_role.json,
        name=f"{STACK_NAME}-bus-api-role",
        managed_policy_arns=[
            bus_managed_policy
        ],
        opts=pulumi.ResourceOptions(parent=event_bus)
    )

    pulumi.export('BusArn', event_bus.arn)
    pulumi.export('BusArchiveArn', event_archive.arn)
    return event_bus.name

# ----------------------------------------------------------------
# API DOMAIN NAME MAPPING FUNCTION
# ----------------------------------------------------------------


def create_api_domain_mapping(cert_name: str, domain_name: str, api_id: str, stage_id, zone_id: str) -> str:
    """
        Creates an API Domain Name Mapping

    Args:
        cert_name (str): The name of the certificate to use for the domain name mapping
        domain_name (str): The domain name to map to the API
        api_id (str): The API ID
        stage_id (str): The API Stage ID
        zone_id (str): The Route53 Zone ID

    Returns:
        str: API Domain Name Mapping ARN
    """
    print(f"Look up Certificate Domain Name: {cert_name}")
    try:
        certificate_lookup = aws.acm.get_certificate(
            domain=cert_name,
            most_recent=True
        )
        print(" * Certificate Exists")
        print(" * Certificate Arn: " + certificate_lookup.arn)
        certificate_arn = certificate_lookup.arn

        pulumi.export('CertificateArn', certificate_lookup.arn)
    except:
        print("Certificate does not exist and NEEDS to be created before running this.")
        sys.exit()

    print("API Domain Name Mapping to be Created: " + domain_name)

    # https: // www.pulumi.com/registry/packages/aws/api-docs/apigateway/domainname/
    api_domain_name = aws.apigatewayv2.DomainName(
        "api-domain-name",
        domain_name=domain_name,
        domain_name_configuration=aws.apigatewayv2.DomainNameDomainNameConfigurationArgs(
            certificate_arn=certificate_arn,
            endpoint_type="REGIONAL",
            security_policy="TLS_1_2",
        )
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/apigatewayv2/apimapping/
    api_domain_mapping = aws.apigatewayv2.ApiMapping(
        "httpApiDomainMapping",
        api_id=api_id,
        domain_name=domain_name,
        stage=stage_id,
        opts=pulumi.ResourceOptions(
            depends_on=[api_domain_name], parent=api_domain_name)
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/route53/record/
    aws.route53.Record(
        "route53-record",
        name=api_domain_name.domain_name,
        type="A",
        zone_id=zone_id,
        aliases=[aws.route53.RecordAliasArgs(
            name=api_domain_name.domain_name_configuration.target_domain_name,
            zone_id=api_domain_name.domain_name_configuration.hosted_zone_id,
            evaluate_target_health=False,
        )],
        opts=pulumi.ResourceOptions(
            depends_on=[api_domain_mapping], parent=api_domain_mapping)
    )

    pulumi.export(
        'apiGatewayDomainName',
        api_domain_name.domain_name_configuration.target_domain_name
    )

    return api_domain_name.domain_name_configuration.target_domain_name


# ----------------------------------------------------------------
# HTTP API Gateway
# ----------------------------------------------------------------
def create_http_api(
        name: str,
        authorizer_type: str,
        authorizer_uri: str,
        authorizer_audience: str,
        bus_name: str,
        api_url: str,
        api_path: str,
        route53_zone_name: str,
        certificate_name: str,
        authorizer_scopes: str = None,
        log_retention_days: int = 7) -> str:
    """
    Creates an API Gateway HTTP API

    Args:
        name (str): The name of the API Gateway HTTP API
        authorizer_type (str): The type of authorizer to use
        authorizer_uri (str): The URI of the authorizer
        authorizer_audience (str): The audience of the authorizer
        bus_name (str): The name of the EventBus
        api_url (str): The URL of the API Gateway
        api_path (str): The path of the API Gateway
        route53_zone_name (str): The name of the Route53 Zone
        certificate_name (str): The name of the certificate to use for the domain name mapping
        authorizer_scopes (str): The scopes of the authorizer
        log_retention_days (int): The number of days to retain the logs

    Returns:
        str: API Gateway HTTP API ID

    """

    # https://www.pulumi.com/registry/packages/aws/api-docs/apigatewayv2/api/
    api = aws.apigatewayv2.Api(
        f"{name}HttpApi",
        name=f"{STACK_NAME}-api",
        protocol_type="HTTP"
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/cloudwatch/loggroup/
    logs = aws.cloudwatch.LogGroup(
        f"{name}HttpApiLogs",
        name=f"/aws/http/{STACK_NAME}-api",
        retention_in_days=log_retention_days,
        opts=pulumi.ResourceOptions(parent=api)
    )

    if authorizer_type == "JWT":
        if authorizer_scopes is not None:
            print("API Scopes to be Added: " + authorizer_scopes)
            AUTHORIZER_SCOPES = [authorizer_scopes]
        else:
            print("No API Scopes to be Added")
            AUTHORIZER_SCOPES = []

        # JWT Authorizer
        # https://www.pulumi.com/registry/packages/aws/api-docs/apigatewayv2/authorizer/
        api_authorizer = aws.apigatewayv2.Authorizer(
            f"{name}HttpApiAuthorizer",
            api_id=api.id,
            identity_sources=[
                "$request.header.Authorization"],
            authorizer_type="JWT",
            jwt_configuration=aws.apigatewayv2.AuthorizerJwtConfigurationArgs(
                issuer=authorizer_uri,
                audiences=[
                    authorizer_audience]
            ),
            opts=pulumi.ResourceOptions(
                depends_on=[api], parent=api)
        )

    # https://www.pulumi.com/registry/packages/aws/api-docs/apigatewayv2/stage/
    api_stage = aws.apigatewayv2.Stage(
        f"{name}HttpApiStage",
        api_id=api.id,
        auto_deploy=True,
        name=ENVIRONMENT,
        access_log_settings=aws.apigatewayv2.StageAccessLogSettingsArgs(
            destination_arn=logs.arn,
            format='{"requestId":"$context.requestId", "ip": "$context.identity.sourceIp", "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod","routeKey":"$context.routeKey", "status":"$context.status","protocol":"$context.protocol", "responseLength":"$context.responseLength","integrationRequestId":"$context.integration.requestId","integrationStatus":"$context.integration.integrationStatus","integrationLatency":"$context.integrationLatency","integrationErrorMessage":"$context.integrationErrorMessage","errorMessageString":"$context.error.message","authorizerError":"$context.authorizer.error"}'
        ),
        opts=pulumi.ResourceOptions(
            depends_on=[api], parent=api)
    )

    # https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-aws-services-reference.html
    # https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_PutEvents.html
    # https://www.pulumi.com/registry/packages/aws/api-docs/apigatewayv2/integration/

    api_bus_integration = aws.apigatewayv2.Integration(
        f"{name}ApiEventBusIntegration",
        api_id=api.id,
        credentials_arn=f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/{STACK_NAME}-bus-api-role",
        integration_type="AWS_PROXY",
        integration_subtype="EventBridge-PutEvents",
        payload_format_version="1.0",
        passthrough_behavior="WHEN_NO_MATCH",
        request_parameters={
            'EventBusName': bus_name,
            'Detail': '$request.body',
            'DetailType': 'PizzaOrder',
            'Source': 'pizza.pineapple.events'
        },
        opts=pulumi.ResourceOptions(
            depends_on=[api], parent=api)
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/apigatewayv2/route/
    print(f"API Path Mapping: {api_path}")
    aws.apigatewayv2.Route(
        f"{name}HttpApiRoute",
        api_id=api.id,
        route_key=api_path,
        authorization_type="JWT",
        authorizer_id=api_authorizer.id.apply(
            lambda id: f"{id}"),
        authorization_scopes=AUTHORIZER_SCOPES,
        target=api_bus_integration.id.apply(
            lambda id: f"integrations/{id}"),
        opts=pulumi.ResourceOptions(
            depends_on=[api], parent=api)
    )

    print("API Domain Name Mapping to be Created: " + api_url)
    print(" * Checking Route53 Zone")

    # Lookup Route53 Zone ID
    try:
        zone_lookup = aws.route53.get_zone(name=route53_zone_name)
        print(f" * Route53 Zone Exists: {zone_lookup.name}")
        print(f" * Route53 Zone Id: {zone_lookup.id}")
        ZONE_ID = zone_lookup.id

        pulumi.export('Route53Id', zone_lookup.id)
        pulumi.export('Route53NsAddresses', zone_lookup.name_servers)
    except:
        print("Route53 Zone does not exists and NEEDS to be created before running this.")
        sys.exit()

    create_api_domain_mapping(
        cert_name=certificate_name, domain_name=api_url, api_id=api.id, stage_id=api_stage.id, zone_id=ZONE_ID)

    return api.id


def create_lambda_function(
        function_name: str,
        runtime: str,
        code_source: str,
        handler: str,
        memory: int,
        queue_arn: str,
        layer_arns: Optional[str] = None,
        x_ray: Optional[bool] = False,
        insights: Optional[bool] = False,
        powertools: Optional[bool] = False,
        architecture: Optional[str] = "x86_64") -> str:
    """
    Creates a Lambda Function

    Args:
        name (str): A name that will be used to create the Lambda Function
        runtime (str): The runtime of the Lambda Function
        code_source (str): The source of the Lambda Function code
        handler (str): The handler of the Lambda Function
        memory (int): The memory of the Lambda Function
        queue_arn (str): The ARN of the SQS Queue
        x_ray (bool): Enable X-Ray tracing
        insights (bool): Enable Lambda Insights
        powertools (bool): Enable PowerTools
        architecture (str): The architecture of the Lambda Function

    Returns:
        str: Lambda Function ARN

    """
    LAMBDA_MANAGED_POLICY_ARNS = []

    print("Lambda Options")
    print(f" * Lambda Architectures: {architecture}")

    if layer_arns is None:
        LAMBDA_LAYERS = []
    else:
        LAMBDA_LAYERS = []
        LAMBDA_LAYER_ARNS = layer_arns.replace(' ', '').split(',')
        LAMBDA_LAYERS.extend(LAMBDA_LAYER_ARNS)
        print(f" + Additional Layers: {LAMBDA_LAYERS}")

    if x_ray is True:
        print(" * Enabling AWS XRay Tracing")
        TRACING_CONFIGURATION = aws.lambda_.FunctionTracingConfigArgs(
            mode="Active")
        LAMBDA_MANAGED_POLICY_ARNS.append(
            "arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess")
        print("   + Adding AWS XRay Managed Policy")
    else:
        TRACING_CONFIGURATION = None

    if insights is True:
        if architecture == "arm64":
            LAMBDA_LAYERS.append(INSIGHTS_LAYER_ARM64)
            print(" + Adding Cloudwatch Lambda Insights Layer - arm64")
        else:
            LAMBDA_LAYERS.append(INSIGHTS_LAYER_X86)
            print(" + Adding Cloudwatch Lambda Insights Layer - x86-64")
        print("   + Adding Cloudwatch Lambda Insights Managed Policy")
        LAMBDA_MANAGED_POLICY_ARNS.append(
            "arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy")

    if powertools is True:
        LAMBDA_LAYERS.append(POWERTOOLS_LAYER)
        print(" + Adding AWS Python Powertools Lambda Layer")

    lambda_assume_role_trust = aws.iam.get_policy_document(statements=[aws.iam.GetPolicyDocumentStatementArgs(
        actions=["sts:AssumeRole"],
        principals=[aws.iam.GetPolicyDocumentStatementPrincipalArgs(
            type="Service",
            identifiers=["lambda.amazonaws.com"]
        )],
    )])

    sqs_trigger_policy = aws.iam.get_policy_document(statements=[aws.iam.GetPolicyDocumentStatementArgs(
        actions=[
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes",
            "sqs:ReceiveMessage"
        ],
        resources=[queue_arn],
    )])

    # https://www.pulumi.com/registry/packages/aws/api-docs/iam/role/
    lambda_role = aws.iam.Role(
        f"{function_name}LambdaRole",
        name_prefix=f"role-{STACK_NAME}",
        assume_role_policy=lambda_assume_role_trust.json,
        inline_policies=[
            aws.iam.RoleInlinePolicyArgs(
                name="SqsLambdaTrigger",
                policy=sqs_trigger_policy.json,
            )
        ],
        managed_policy_arns=LAMBDA_MANAGED_POLICY_ARNS,
        opts=pulumi.ResourceOptions(
            delete_before_replace=True)
    )

    # Attach the fullaccess policy to the Lambda role created above
    aws.iam.RolePolicyAttachment(
        f"{function_name}LambdaRoleAttachment",
        role=lambda_role,
        policy_arn=aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE,
        opts=pulumi.ResourceOptions(
            parent=lambda_role)
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/lambda/function/
    lambda_function = aws.lambda_.Function(
        f"{function_name}LambdaFunction",
        code=pulumi.AssetArchive({
            ".": pulumi.FileArchive(f"{code_source}"),
        }),
        runtime=runtime,
        role=lambda_role.arn,
        name=f"{STACK_NAME}-{function_name}",
        handler=handler,
        layers=LAMBDA_LAYERS,
        memory_size=memory,
        tracing_config=TRACING_CONFIGURATION,
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "ENVIRONMENT": ENVIRONMENT
            }),
        opts=pulumi.ResourceOptions(
            depends_on=[lambda_role])
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/lambda/eventsourcemapping/
    aws.lambda_.EventSourceMapping(
        f"{function_name}LambdaSourceMapping",
        event_source_arn=queue_arn,
        function_name=lambda_function.arn,
        opts=pulumi.ResourceOptions(
            parent=lambda_function)
    )

    pulumi.export('LambdaFunctionArn', lambda_function.arn)
    return lambda_function.arn


# ----------------------------------------------------------------
# SQS Queue and Queue Policy
# ----------------------------------------------------------------
def create_sqs_queue(name: str) -> str:
    """
    Creates a SQS Queue

    Args:
        name (str): A name that will be used to create the SQS Queue

    Returns:
        str: SQS Queue ARN
    """
    print("SQS Queue")
    sqs_queue = aws.sqs.Queue(
        f"{name}Queue",
        name=f"{STACK_NAME}-{name}-queue",
    )

    sqs_queue_policy = aws.iam.get_policy_document(statements=[
        aws.iam.GetPolicyDocumentStatementArgs(
            sid="HttpApiToSqs",
            principals=[aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                type="Service",
                identifiers=["events.amazonaws.com"],
            )],
            conditions=[aws.iam.GetPolicyDocumentStatementConditionArgs(
                test="ArnEquals",
                variable="aws:SourceArn",
                values=[
                    sqs_queue.arn
                ],
            )]
        )]
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/sqs/queuepolicy/
    aws.sqs.QueuePolicy(
        f"{name}QueuePolicy",
        queue_url=sqs_queue.id,
        policy=sqs_queue_policy.json,
        opts=pulumi.ResourceOptions(parent=sqs_queue)
    )

    print(f" + Name: {STACK_NAME}-{name}-queue")
    pulumi.export(f"sqs{name}", sqs_queue.arn)
    return sqs_queue.arn


# ----------------------------------------------------------------
# Event Rule and Event Target
# ----------------------------------------------------------------

def create_rule_and_sqs_target(name: str, bus_name: str, rule_pattern: str, queue_target_arn: str, enabled: Optional[bool] = True,) -> str:
    """
    Creates a Event Rule and Event Target for a SQS Queue

    Args:
        name (str): A name that will be used to create the Event Rule and Event Target
        bus_name (str): The EventBridge Bus Name
        rule_pattern (str): Rule Pattern as a JSON string
        queue_target_arn (str): The SQS Queue ARN
        enabled (bool, optional): [description]. Defaults to True.

    Returns:
        str: Events Rule ARN
    """

    # https://www.pulumi.com/registry/packages/aws/api-docs/cloudwatch/eventrule/
    event_rule = aws.cloudwatch.EventRule(
        f"{name}Rule",
        name=f"{STACK_NAME}-{name}-rule",
        event_bus_name=bus_name,
        is_enabled=enabled,
        event_pattern=rule_pattern,
    )

    # https://www.pulumi.com/registry/packages/aws/api-docs/cloudwatch/eventtarget/
    aws.cloudwatch.EventTarget(
        f"{name}RuleTarget",
        arn=queue_target_arn,
        event_bus_name=bus_name,
        rule=event_rule.name,
        opts=pulumi.ResourceOptions(
            parent=event_rule)
    )

    pulumi.export(f"eventRule{name}", event_rule.arn)
    return event_rule.arn
