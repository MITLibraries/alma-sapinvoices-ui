import boto3

from attrs import define


@define
class ECSClient:
    """ECS Client for running and monitoring task runs."""

    cluster: str
    task_definition: str
    network_configuration: dict

    @property
    def client(self):
        return boto3.client("ecs")

    @property
    def container_name(self):
        return self.cluster.split("/")[-1]

    def execute_review_run(self):
        response = self.client.run_task(
            cluster=self.cluster,
            launchType="FARGATE",
            networkConfiguration=self.network_configuration,
            overrides={
                "containerOverrides": [
                    {
                        "name": self.container_name,
                        "command": [
                            "--run_connection_tests",
                            "--ignore_sns_logging",
                        ],  # [TODO] Update for SAP Invoices
                    }
                ]
            },
            taskDefinition=self.task_definition,
        )

        return response


if __name__ == "__main__":
    from config import Config

    ecs_client = ECSClient(
        cluster=Config.ALMA_SAP_INVOICES_ECS_CLUSTER,
        task_definition=Config.ALMA_SAP_INVOICES_ECS_TASK_DEFINITION,
        network_configuration=Config.ALMA_SAP_INVOICES_ECS_NETWORK_CONFIG,
    )
    print("Tada!")
