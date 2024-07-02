# SAP Invoices Flask App

A Flask application run in AWS Lambda used to process invoices from Alma. Invoice processing is achieved by executing the ECS task that serves the [Alma SAP Invoices CLI](https://github.com/MITLibraries/alma-sapinvoices). The purpose of this web app is to provide a web accessible, graphical interface through which users can easily execute and monitor invoice processing. 

## Development

- To preview a list of available Makefile commands: `make help`
- To install with dev dependencies: `make install`
- To update dependencies: `make update`
- To run unit tests: `make test`
- To lint the repo: `make lint`

### Running the Flask App Locally

1. Run the following command with `pipenv`: 
  ```
  pipenv run sapinvoices_flask_app
  ```

2. Visit http://127.0.0.1:5000.
   
## Environment Variables

### Required

```shell
ALMA_SAP_INVOICES_ECR_IMAGE_NAME=### The name of the ECR image for the Alma SAP Invoices CLI.
ALMA_SAP_INVOICES_ECS_CLUSTER=### The short name or full ARN of the ECS cluster to run the Alma SAP Invoices CLI ECS task.
ALMA_SAP_INVOICES_ECS_TASK_DEFINITION=### The family and revision (formatted as <family>:<revision>) or full ARN of Alma SAP Invoices CLI ECS task. 
ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG=### The network configuration for the Alma SAP Invoices ECS task.
ALMA_SAP_INVOICES_CLOUDWATCH_LOG_GROUP=### The name of the log group containing logs from Alma SAP Invoices ECS task runs.
SENTRY_DSN=### If set to a valid Sentry DSN, enables Sentry exception monitoring. This is not needed for local development.
WORKSPACE=### Set to `dev` for local development, this will be set to `stage` and `prod` in those environments by Terraform.
```