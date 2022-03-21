# Pulumi - AWS HTTP API, EventBridge, Lambda

- [Pulumi - AWS HTTP API, EventBridge, Lambda](#pulumi---aws-http-api-eventbridge-lambda)
  - [Purpose](#purpose)
  - [How To Use](#how-to-use)
    - [Inputs](#inputs)
  - [Getting Started](#getting-started)
    - [Poetry](#poetry)
      - [Installing without poetry.lock](#installing-without-poetrylock)
      - [Installing with poetry.lock](#installing-with-poetrylock)
      - [Commit your poetry.lock file to version control](#commit-your-poetrylock-file-to-version-control)
  - [Optional Inputs](#optional-inputs)

## Purpose

This package creates an AWS HTTP API (APIGatewayV2) with an integration to EventBridge. This will also create an EventBridge Rule that targets a SQS Queue that will then trigger the Lambda.

## How To Use

In this repository there is an example environment file named `Pulumi.ENV.yaml` that contains some example values. Those values and the `ENV` will need to be modified to what you want to create.

### Inputs
| Name                      | Type   | Required | Description                                                                               |
| ------------------------- | ------ | -------- | ----------------------------------------------------------------------------------------- |
| `code_source`             | string | Yes      | The location in your repository where the Lambda code resides.                            |
| `function_name`           | string | Yes      | Lambda Function Name                                                                      |
| `handler`                 | string | Yes      | The Lambda function handler is the method in your function code that processes events     |
| `memory`                  | string | Yes      | The amount of memory the Lambda Function will be provisioned with                         |
| `runtime`                 | string | Yes      | AWS Lambda Runtime the Lambda Fucntion will be created with                               |
| `lambda_architecture`     | string | No       | The instruction set architecture of a Lambda function. Default: `x86_64` - Allowed Values: `arm64`, `x86_64` |
| ------------------------- | ------ | -------- | ----------------------------------------------------------------------------------------- |
| `authorizer_type`         | string | No       | (Optional) Type of authorizer.  - Allowed Values:  `JWT`                                  |
| `authorizer_audience`     | string | No       | (Conditional) If using an authorizer, specify an audience.                                |
| `authorizer_uri`          | string | No       | (Conditional) If using an authorizer, specify the authorizer URI.      |
| `authorizer_scopes`       | string | No       | (Optional) If you have any scopes, specify these as a command seperated string.           |
| ------------------------- | ------ | -------- | ----------------------------------------------------------------------------------------- |
| `api_path`                | string | Yes      | The Method and API Path that the HTTP API will listen on                                  |
| `create_api_mapping`      | boolean| No       | (Optional) Create a API Gateway API Domain Name Mapping                                   |
| `certificate_name`        | string | No       | (Conditional) The ACM certificate name that the module will look up to find its ARN.      |
| `route53_zone_name`       | string | No       | (Conditional) If you are creating an API mapping, specify the Route53 zone you want.      |
| `url`                     | string | No       | (Conditional) If you are creating an API mapping, specify API URL.                        |
| ------------------------- | ------ | -------- | ----------------------------------------------------------------------------------------- |
| `enable_xray_tracing`     | boolean| No       | (Optional) Enable AWS X-Ray Tracing  - Allowed Values: `true` or `false`                  |
| `add_insights_layer`      | boolean| No       | (Optional) AWS Lambda Insights Lambda Layer  - Allowed Values: `true` or `false`          |
| `add_powertools_layer`    | boolean| No       | (Optional) AWS Python PowerTools Layer - Allowed Values: `true` or `false`                |
| `lambda_layer_arns`       | string | No       | (Optional) Comma seperate string of layers you want to attach                             |



## Getting Started

### Poetry

* This module is set up with Poetry.  You can view the Poetry [install directions here](https://python-poetry.org/docs/#installation).

Poetry is similar to other package managers that exist out there.  To install the defined dependencies for this project you just need to run the following.

```
poetry install
```

#### Installing without poetry.lock


If you have never run the command before and there is also no `poetry.lock` file present, Poetry simply resolves all dependencies listed in your `pyproject.toml`file and downloads the latest version of their files.

When Poetry has finished installing, it writes all of the packages and the exact versions of them that it downloaded to the `poetry.lock` file, locking the project to those specific versions. You should commit the `poetry.lock` file to your project repo so that all people working on the project are locked to the same versions of dependencies.

#### Installing with poetry.lock
This brings us to the second scenario. If there is already a `poetry.lock` file as well as a `pyproject.toml` file when you run `poetry install`, it means either you ran the install command before, or someone else on the project ran the `install` command and committed the `poetry.lock` file to the project (which is good).

Either way, running `install` when a `poetry.lock` file is present resolves and installs all dependencies that you listed in `pyproject.toml`, but Poetry uses the exact versions listed in `poetry.lock` to ensure that the package versions are consistent for everyone working on your project. As a result you will have all dependencies requested by your `pyproject.toml` file, but they may not all be at the very latest available versions (some of the dependencies listed in the `poetry.lock` file may have released newer versions since the file was created). This is by design, it ensures that your project does not break because of unexpected changes in dependencies.

#### Commit your poetry.lock file to version control

Committing this file to VC is important because it will cause anyone who sets up the project to use the exact same versions of the dependencies that you are using. Your CI server, production machines, other developers in your team, everything and everyone runs on the same dependencies, which mitigates the potential for bugs affecting only some parts of the deployments. Even if you develop alone, in six months when reinstalling the project you can feel confident the dependencies installed are still working even if your dependencies released many new versions since then.


## Optional Inputs
