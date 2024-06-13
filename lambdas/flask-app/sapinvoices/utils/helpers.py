def get_task_id_from_arn(task_arn: str):
    return task_arn.split("/")[-1]
