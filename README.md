# Pulumi - AWS HTTP API to Lambda

- [Pulumi - AWS HTTP API to Lambda](#pulumi---aws-http-api-to-lambda)
  - [Purpose](#purpose)
  - [How To Use](#how-to-use)
    - [Inputs](#inputs)
  - [Getting Started](#getting-started)
  - [Optional Inputs](#optional-inputs)

## Purpose

This package creates an AWS HTTP API (APIGatewayV2) with an integration to a Lambda function.

## How To Use

In this repository there is an example environment file named `Pulumi.ENV.yaml` that contains some example values. Those values and the `ENV` will need to be modified to what you want to create.

### Inputs
| Name                      | Type   | Required | Description                                                                               |
| ------------------------- | ------ | -------- | ----------------------------------------------------------------------------------------- |
| `layer-lambda_memory`     | string | Yes      | The amount of memory the Lambda Function will be provisioned with                         |
| `lambda_runtime`          | string | Yes      | AWS Lambda Runtime the Lambda Fucntion will be created with                               |
| `lambda_handler`          | string | Yes      | The Lambda function handler is the method in your function code that processes events     |
| `lambda_architecture`     | string | No       | The instruction set architecture of a Lambda function. Default: `x86_64` - Allowed Values: `arm64`, `x86_64` |
| `authorizer_type`         | string | No       | (Optional) An optional prefix that will be used for a folder path inside the S3 bucket    |
| `principal`               | string | Yes      | An AWS Account ID to grant layer usage permissions to                                     |
| `authorizer_type`         | string | No       | (Optional) An optional prefix that will be used for a folder path inside the S3 bucket    |
| `authorizer_audience`     | string | Yes      | An AWS Account ID to grant layer usage permissions to                                     |
| `authorizer_uri`          | string | No       | (Optional) An optional prefix that will be used for a folder path inside the S3 bucket    |
| `authorizer_scopes`       | string | Yes      | An AWS Account ID to grant layer usage permissions to                                     |
| `route53_zone_name`       | string | No       | (Optional) An optional prefix that will be used for a folder path inside the S3 bucket    |
| `api_url`                 | string | Yes      | An AWS Account ID to grant layer usage permissions to                                     |
| `certificate_domain_name` | string | No       | (Optional) An optional prefix that will be used for a folder path inside the S3 bucket    |
| `create_api_mapping`      | boolean| No       | (Optional) Create a API Gateway API Domain Name Mapping                                   |
| `enable_xray_tracing`     | boolean| No       | (Optional) Enable AWS X-Ray Tracing  - Allowed Values: `True` or `False`                  |
| `add_insights_layer`      | boolean| No       | (Optional) AWS Lambda Insights Lambda Layer  - Allowed Values: `True` or `False`          |
| `add_powertools_layer`    | boolean| No       | (Optional) AWS Python PowerTools Layer - Allowed Values: `True` or `False`   |
| `lambda_layer_arns`       | string | No       | (Optional) Comma seperate string of layers you want to attach                             |



## Getting Started



## Optional Inputs
