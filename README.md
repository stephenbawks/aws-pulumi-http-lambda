# Pulumi - AWS HTTP API, EventBridge, Lambda

- [Pulumi - AWS HTTP API, EventBridge, Lambda](#pulumi---aws-http-api-eventbridge-lambda)
  - [Purpose](#purpose)
  - [How To Use](#how-to-use)
    - [Inputs](#inputs)
  - [Infrastructure Diagram](#infrastructure-diagram)
  - [Getting Started](#getting-started)
    - [Prerequisite](#prerequisite)
    - [Environments or Stacks](#environments-or-stacks)
    - [Up](#up)

## Purpose

This package creates an AWS HTTP API (APIGatewayV2) with an integration to EventBridge. This will also create an EventBridge Rule that targets a SQS Queue that will then trigger the Lambda.

<a href="https://app.pulumi.com/new?template=https://github.com/stephenbawks/pulumi-http-eventbridge-lambda" rel="nofollow"><img src="https://camo.githubusercontent.com/4ce4c9f9d2258c141f1151c02886342d68858e7b62b291c7a913f082f7c4c0a7/68747470733a2f2f6765742e70756c756d692e636f6d2f6e65772f627574746f6e2e737667" alt="Deploy with Pulumi" data-canonical-src="https://get.pulumi.com/new/button.svg" style="max-width: 100%;"></a>


## How To Use

The template assumes a couple of things.  There is the concept around having values specified inside the `__main__.py` file.  These would be values that do not change from environment to environment or stack to stack.  Typically I would describe these as your `Set it and Forget it` type variables.

However there are values that you very well may want to change in different environments.  A couple example of this may be the memory you dedicate to a Lambda Function.  In `nonprod` you may only want `128` whereas in `prod` you may want it to be `256`. Another good example might be your API URL address.  You probably will want to have a separate URL in `nonprod` vs `prod` (or however you name your environments).

In this repository there is an example environment file named `Pulumi.ENV.yaml` that contains some example values. Those values and the `ENV` will need to be modified to what you want to create.

### Inputs
| Name                      | Type   | Required | Variable Location | Description                                                           |
| ------------------------- | ------ | -------- | ----------------- | --------------------------------------------------------------------- |
| `code_source`             | string | Yes      | `template`        | The location in your repository where the Lambda code resides.        |
| `function_name`           | string | Yes      | `template`        | Lambda Function Name                                                                      |
| `handler`                 | string | Yes      | `template`        | The Lambda function handler is the method in your function code that processes events     |
| `memory`                  | string | Yes      | `stack`           | The amount of memory the Lambda Function will be provisioned with                         |
| `runtime`                 | string | Yes      | `template`        | AWS Lambda Runtime the Lambda Fucntion will be created with                               |
| `lambda_architecture`     | string | No       | `template`        | The instruction set architecture of a Lambda function. Default: `x86_64` - Allowed Values: `arm64`, `x86_64` |
|  |
| `authorizer_type`         | string | No       | `template`        | (Optional) Type of authorizer.  - Allowed Values:  `JWT`                                  |
| `authorizer_audience`     | string | No       | `stack`           | (Conditional) If using an authorizer, specify an audience.                                |
| `authorizer_uri`          | string | No       | `stack`           | (Conditional) If using an authorizer, specify the authorizer URI.      |
| `authorizer_scopes`       | string | No       | `stack`           | (Optional) If you have any scopes, specify these as a command seperated string.           |
|  |
| `api_path`                | string | Yes      | `template`        | The Method and API Path that the HTTP API will listen on                                  |
| `create_api_mapping`      | boolean| No       | `template`        | (Optional) Create a API Gateway API Domain Name Mapping                                   |
| `certificate_name`        | string | No       | `stack`           | (Conditional) The ACM certificate name that the module will look up to find its ARN.      |
| `route53_zone_name`       | string | No       | `stack`           | (Conditional) If you are creating an API mapping, specify the Route53 zone you want.      |
| `url`                     | string | No       | `stack`           | (Conditional) If you are creating an API mapping, specify API URL.                        |
| |
| `enable_xray_tracing`     | boolean| No       | `template`        | (Optional) Enable AWS X-Ray Tracing  - Allowed Values: `true` or `false`                  |
| `add_insights_layer`      | boolean| No       | `template`        | (Optional) AWS Lambda Insights Lambda Layer  - Allowed Values: `true` or `false`          |
| `add_powertools_layer`    | boolean| No       | `template`        | (Optional) AWS Python PowerTools Layer - Allowed Values: `true` or `false`                |
| `lambda_layer_arns`       | string | No       | `stack`           | (Optional) Comma seperate string of layers you want to attach                             |



## Infrastructure Diagram

Here is a diagram of what this template will be building.

## Getting Started

### Prerequisite

There are some prerequisites that need to be in place before you can get this up and running.  This template is set up with Poetry to handle the packaging/dependencies.  This template also have two resources that I generally advise you to create them out-of-band or via another IAC module.  Those two are:
* ACM Certificate
* Route53 Zone

The main reason for this is that if you accidently make a mistake in this template or tear it down you may very well not want to have your Route53 zone removed as that may result in other possible infrastructure being affected, upstream or downstream for yours.  Second is the ACM certificate.  If you remove that, you will have to through and re-create that and re-associate it with any infrastructure that may be using that.

Both of these resources need to be pre-created if you are going to be using a custom domain name mapping to use with your HTTP API Gateway.  If you do not neeed those, then you do not need to worry about them and can skip creating them.


### Environments or Stacks

Pulumi has the ability to create indenpendent environments or called a stack.  It represents that as a key-value pairs stored in a stack settings file named `Pulumi.<stackname>.yaml`.  For example, lets say you have two different environments that you have named `nonprod` and `prod`.  You would represent those by having two aptly named files in your respository named `Pulumi.nonprod.yaml` and `Pulumi.prod.yaml`.  This allows you to have different configurations for each environment.  If your `prod` environment needs more memory than your `nonprod` environment you can change your `Pulumi.prod.yaml` to represent that so that this will not affect infrastructure in your `nonprod` environment.

Included in this respository there is a single file that is named `Pulumi.nonprod.yaml` that can be used for getting started quickly.

### Up

Enough with the documentaiton, lets get started!

The command to create and or update resources in a stack is [`pulumi up`](https://www.pulumi.com/docs/reference/cli/pulumi_up/). The new desired goal state for the target stack is computed by running the current Pulumi program and observing all resource allocations to produce a resource graph. This goal state is then compared against the existing state to determine what create, read, update, and/or delete operations must take place to achieve the desired goal state, in the most minimally disruptive way. This command records a full transactional snapshot of the stack’s new state afterwards so that the stack may be updated incrementally again later on.


