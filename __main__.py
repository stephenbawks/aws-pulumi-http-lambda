"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws


conf = pulumi.Config()
AWS_ACCOUNT_ID = (aws.get_caller_identity()).account_id
AWS_REGION = (aws.get_region()).name

ENVIRONMENT = pulumi.get_stack()
APP_NAME = pulumi.get_project()
STACK_NAME = f"{ENVIRONMENT}-{APP_NAME}"

LAMBDA_MEMORY = conf.get_int("lambda_memory")
LAMBDA_RUNTIME = conf.get("lambda_runtime")
LAMBDA_HANDLER = conf.get("lambda_handler")
INSIGHTS_LAYER = f"arn:aws:lambda:{AWS_REGION}:580247275435:layer:LambdaInsightsExtension:16"
POWERTOOLS_LAYER = f"arn:aws:lambda:{AWS_REGION}:017000801446:layer:AWSLambdaPowertoolsPython:6"


aws.Provider('aws',
    default_tags=aws.provider.ProviderDefaultTagsArgs(
        tags={
            "iac": "pulumi",
            "user:Project": APP_NAME,
            "user:Stack": ENVIRONMENT,
            "module": "aws-pulumi-http-lambda",
            "module_source": "https://github.com/stephenbawks/aws-pulumi-http-lambda",
            "module_version": "0.0.1",
        }
    )
)

tags={}


# ----------------------------------------------------------------
# API DOMAIN NAME MAPPING FUNCTION
# ----------------------------------------------------------------
def create_api_domain_mapping(acm_cert_arn: str, domain_name: str, api_id: str, stage_id, zone_id: str) -> str:
    print("API Domain Name Mapping to be Created: " + domain_name)

    apiDomainName = aws.apigatewayv2.DomainName("httpApiDomainName",
        domain_name=domain_name,
        domain_name_configuration=aws.apigatewayv2.DomainNameDomainNameConfigurationArgs(
            certificate_arn=acm_cert_arn,
            endpoint_type="REGIONAL",
            security_policy="TLS_1_2",
        ),
        tags=tags
    )

    apiDomainMapping = aws.apigatewayv2.ApiMapping("httpApiDomainMapping",
        api_id=api_id,
        domain_name=domain_name,
        stage=stage_id
    )

    apiRoute53Record = aws.route53.Record("route53Record",
        name=apiDomainName.domain_name,
        type="A",
        zone_id=zone_id,
        aliases=[aws.route53.RecordAliasArgs(
            name=apiDomainName.domain_name_configuration.target_domain_name,
            zone_id=apiDomainName.domain_name_configuration.hosted_zone_id,
            evaluate_target_health=False,
        )]
    )

    pulumi.export('apiGatewayDomainName', apiDomainName.domain_name_configuration.target_domain_name)
    return apiDomainName.domain_name_configuration.target_domain_name


# ----------------------------------------------------------------
# ROUTE53
# ----------------------------------------------------------------

checkZone = conf.get("route53_zone_name")
if checkZone and checkZone.strip():
    ROUTE53_ZONE = conf.get("route53_zone_name")

    try:
        zone_lookup = aws.route53.get_zone(name=ROUTE53_ZONE)
        print("Route53 Zone Exists")
        print("Route53 Zone Selected: " + zone_lookup.name)
        print("Route53 Zone Id: " + zone_lookup.id)
        ZONE_ID = zone_lookup.id

        pulumi.export('Route53Id', zone_lookup.id)
        pulumi.export('Route53NsAddresses', zone_lookup.name_servers)
    except:
        print("Route53 Zone does not exists and NEEDS to be created before running this.")
        exit()


# ----------------------------------------------------------------
# CERTIFICATE
# ----------------------------------------------------------------

checkCertificate = conf.get("certificate_domain_name")
if checkCertificate and checkCertificate.strip():
    checkCertificate = conf.get("certificate_domain_name")

    print("Look up Certificate Domain Name: " + checkCertificate)
    try:
        certificate_lookup = aws.acm.get_certificate(domain=checkCertificate,
            most_recent=True
        )
        print(" * Certificate Exists")
        print(" * Certificate Id: " + certificate_lookup.id)
        CERTIFICATE_ARN = certificate_lookup.arn

        pulumi.export('CertificateArn', certificate_lookup.arn)
    except:
        print("Certificate does not exist and NEEDS to be created before running this.")
        exit()



# ----------------------------------------------------------------
# HTTP API Gateway
# ----------------------------------------------------------------

logs = aws.cloudwatch.LogGroup("httpApiLogs",
    name=f"/aws/http/{STACK_NAME}-api",
    retention_in_days=7,
    tags=tags
)

api = aws.apigatewayv2.Api("httpApi",
    name=f"{STACK_NAME}-api",
    protocol_type="HTTP",
    tags=tags
)

AUTHORIZER_TYPE = (conf.get("authorizer_type").upper())

if AUTHORIZER_TYPE == "JWT":
    AUTHORIZER_AUDIENCE = [conf.get("authorizer_audience")]
    AUTHORIZER_URI = conf.get("authorizer_uri")
    checkScopes = conf.get("authorizer_scopes")
    if checkScopes and checkScopes.strip():
        print("API Scopes to be Added: " + checkScopes)
        AUTHORIZER_SCOPES = [conf.get("authorizer_scopes")]
    else:
        print("No API Scopes to be Added")
        AUTHORIZER_SCOPES = []

    # JWT Authorizer is True
    apiAuthorizer = aws.apigatewayv2.Authorizer("httpApiAuthorizer",
        api_id=api.id,
        identity_sources=["$request.header.Authorization"],
        authorizer_type="JWT",
        jwt_configuration=aws.apigatewayv2.AuthorizerJwtConfigurationArgs(
            issuer=AUTHORIZER_URI,
            audiences=AUTHORIZER_AUDIENCE
        )
    )

    apiAuthorizerId = apiAuthorizer.id

apiStage = aws.apigatewayv2.Stage("httpApiStage",
    api_id=api.id,
    auto_deploy=True,
    name=ENVIRONMENT,
    access_log_settings=aws.apigatewayv2.StageAccessLogSettingsArgs(
        destination_arn=logs.arn,
        format='{"requestId":"$context.requestId", "ip": "$context.identity.sourceIp", "requestTime":"$context.requestTime", "httpMethod":"$context.httpMethod","routeKey":"$context.routeKey", "status":"$context.status","protocol":"$context.protocol", "responseLength":"$context.responseLength","integrationRequestId":"$context.integration.requestId","integrationStatus":"$context.integration.integrationStatus","integrationLatency":"$context.integrationLatency","integrationErrorMessage":"$context.integrationErrorMessage","errorMessageString":"$context.error.message","authorizerError":"$context.authorizer.error"}'
    ),
    tags=tags
)


CREATE_API_MAPPING = conf.get("create_api_mapping")
if CREATE_API_MAPPING and CREATE_API_MAPPING.lower() == "true":
    API_URL = conf.get("api_url")

    # Uses ZONE_ID from above in the ROUTE53 section
    customDomainName = create_api_domain_mapping(acm_cert_arn=CERTIFICATE_ARN, domain_name=API_URL, api_id=api.id, stage_id=apiStage.id, zone_id=ZONE_ID)
else:
    print("No Domain Name Mapping")



# ----------------------------------------------------------------
# Lambda
# ----------------------------------------------------------------

# Any Lambda Layers you want might to add here, comma separated
LAMBDA_LAYERS = [
        "arn:aws:lambda:us-east-2:547201116507:layer:python-lambda-layer-09_12_2021:3"
    ]

# Any Managed Policies you want might to add here, comma separated
LAMBDA_MANAGED_POLICY_ARNS=[]

print("Lambda Options")
ENABLE_XRAY_TRACING = conf.get("enable_xray_tracing")
if ENABLE_XRAY_TRACING and ENABLE_XRAY_TRACING.lower() == "true":
    print(f" * Enabling AWS XRay Tracing")
    TRACING_CONFIGURATION = aws.lambda_.FunctionTracingConfigArgs(mode="Active")
    LAMBDA_MANAGED_POLICY_ARNS.append("arn:aws:iam::aws:policy/AWSXrayWriteOnlyAccess")
    print("   + Adding AWS XRay Managed Policy")
else:
    TRACING_CONFIGURATION = None

ADD_INSIGHTS_LAYER = conf.get("add_insights_layer")
if ADD_INSIGHTS_LAYER and ADD_INSIGHTS_LAYER.lower() == "true":
    LAMBDA_LAYERS.append(INSIGHTS_LAYER)
    print(" + Adding Cloudwatch Lambda Insights Layer")
    LAMBDA_MANAGED_POLICY_ARNS.append("arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy")
    print("   + Adding Cloudwatch Lambda Insights Managed Policy")

ADD_POWERTOOLS_LAYER = conf.get("add_powertools_layer")
if ADD_POWERTOOLS_LAYER and ADD_POWERTOOLS_LAYER.lower() == "true":
    LAMBDA_LAYERS.append(POWERTOOLS_LAYER)
    print(" + Adding AWS Python Powertools Lambda Layer")

if not ENABLE_XRAY_TRACING and not ADD_POWERTOOLS_LAYER and not ADD_INSIGHTS_LAYER:
    print(" - No additional Lambda Layers or policies")
elif bool(ENABLE_XRAY_TRACING) is False and bool(ADD_POWERTOOLS_LAYER) is False and bool(ADD_INSIGHTS_LAYER) is False:
    print(" - No additional Lambda Layers or policies")

lambdaAssumeRoleTrust = aws.iam.get_policy_document(statements=[aws.iam.GetPolicyDocumentStatementArgs(
    actions=["sts:AssumeRole"],
    principals=[aws.iam.GetPolicyDocumentStatementPrincipalArgs(
        type="Service",
        identifiers=["lambda.amazonaws.com"]
    )],
)])

# https://www.pulumi.com/registry/packages/aws/api-docs/iam/role/
lambda_role = aws.iam.Role("lambdaRole",
    name_prefix=f"role-{STACK_NAME}",
    assume_role_policy=lambdaAssumeRoleTrust.json,
    managed_policy_arns=LAMBDA_MANAGED_POLICY_ARNS,
    tags=tags,
    opts=pulumi.ResourceOptions(delete_before_replace=True)
)

# Attach the fullaccess policy to the Lambda role created above
role_policy_attachment = aws.iam.RolePolicyAttachment("lambdaRoleAttachment",
    role=lambda_role,
    policy_arn=aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE)

# https://www.pulumi.com/registry/packages/aws/api-docs/lambda/function/
lambda_function = aws.lambda_.Function("lambdaFunction",
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("./src"),
    }),
    runtime=LAMBDA_RUNTIME,
    role=lambda_role.arn,
    handler=LAMBDA_HANDLER,
    layers=LAMBDA_LAYERS,
    memory_size=LAMBDA_MEMORY,
    tracing_config=TRACING_CONFIGURATION,
    tags=tags
)

# https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-aws-services-reference.html
# https://www.pulumi.com/registry/packages/aws/api-docs/apigatewayv2/integration/
lambdaIntegration = aws.apigatewayv2.Integration("httpApiLambdaIntegration",
    api_id=api.id,
    integration_type="AWS",
    connection_type="INTERNET",
    integration_uri=lambda_function.invoke_arn,
    passthrough_behavior="WHEN_NO_MATCH",
    integration_method="POST",
    payload_format_version="2.0",
    opts=pulumi.ResourceOptions(depends_on=[lambda_function])
)

lambdaPermission = aws.lambda_.Permission("httpApiLambdaPermission",
    action="lambda:InvokeFunction",
    function=lambda_function,
    principal="apigateway.amazonaws.com",
    source_arn=api.execution_arn.apply(lambda execution_arn: f"{execution_arn}/*/*"),
)


# ----------------------------------------------------------------
# OUTPUTS
# ----------------------------------------------------------------
pulumi.export('LambdaFunctionArn', lambda_function.arn)
pulumi.export('HttpApiId', api.id)
pulumi.export('HttpApiUrl', api.api_endpoint)