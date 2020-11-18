from aws_cdk import (core, aws_lambda, aws_logs,
                     aws_secretsmanager as secretsmanager, aws_events, aws_events_targets)
import subprocess
import os


class TwitterCottonStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        export_sales = aws_lambda.Function(self, "export-sales",
                                           runtime=aws_lambda.Runtime.PYTHON_3_7,
                                           handler="handler.main",
                                           code=aws_lambda.AssetCode(
                                               "./functions/export-sales"),
                                           timeout=core.Duration.seconds(20),
                                           log_retention=aws_logs.RetentionDays.ONE_MONTH,
                                           layers=[self.create_dependencies_layer(
                                               id, "export-sales")]
                                           )

        # Use an existing secret
        secret = secretsmanager.Secret.from_secret_name_v2(self, 'twitter', 'twitter')
        secret.grant_read(export_sales)

        # Runs at two different hours to account for daylight savings
        schedule = aws_events.Rule(
            self, "schedule", schedule=aws_events.Schedule.expression("cron(30,31,33,36,40,45,50,55 12,13 ? * MON,TUE,THU,FRI *)"))

        schedule.add_target(aws_events_targets.LambdaFunction(export_sales))

    def create_dependencies_layer(self, project_name, function_name: str) -> aws_lambda.LayerVersion:
        requirements_file = "functions/" + function_name + "/requirements.txt"
        output_dir = ".functions/" + function_name

        # Install requirements for layer in the output_dir
        if not os.environ.get("SKIP_PIP"):
            # Note: Pip will create the output dir if it does not exist
            subprocess.check_call(
                f"pip3 install -r {requirements_file} -t {output_dir}/python --upgrade".split()
            )
        return aws_lambda.LayerVersion(
            self,
            project_name + "-" + function_name + "-dependencies",
            code=aws_lambda.Code.from_asset(output_dir)
        )
