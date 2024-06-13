import time

import boto3


class CloudWatchClient:

    def __init__(self, log_group: str) -> None:
        self.log_group = log_group

    @property
    def client(self):
        return boto3.client("logs")

    def get_task_result(self, start_time: int, end_time: int, query: str):
        response = self.client.start_query(
            logGroupName=self.log_group,
            startTime=start_time,
            endTime=end_time,
            queryString=query,
        )
        query_id = response["queryId"]
        while True:
            time.sleep(1)
            query_results = self.client.get_query_results(queryId=query_id)
            if query_results["status"] in [
                "Complete",
                "Failed",
                "Cancelled",
                "Timeout",
                "Unknown",
            ]:
                return query_results.get("results", [])
