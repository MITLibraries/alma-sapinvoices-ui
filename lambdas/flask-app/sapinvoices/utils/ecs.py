import boto3


class ECSClient:

    def __init__(self, cluster: str, network_configuration: dict) -> None:
        self.cluster = cluster
        self.network_configuration = network_configuration

    @property
    def client(self):
        return boto3.client("ecs")

    def run_task(self, **kwargs) -> dict:
        return self.client.run_task(
            cluster=self.cluster,
            launchType="FARGATE",
            networkConfiguration=self.network_configuration,
            **kwargs
        )

    def get_task_status(self, tasks: list[str]) -> dict:
        return self.client.describe_tasks(cluster=self.cluster, tasks=tasks)
