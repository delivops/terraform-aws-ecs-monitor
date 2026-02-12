# ECS Events Example

This example shows how to enable capturing all ECS events (task state changes, service actions, container instance state changes) to a CloudWatch Log Group.

## Usage

```bash
terraform init
terraform plan
terraform apply
```

## Configuration

Update the `terraform.tfvars` file with your specific values before applying.

## Outputs

After applying, you can view all ECS events in CloudWatch Logs at:
- Log Group: `/aws/ecs/monitoring/{cluster_name}/ecs-events`

Use CloudWatch Logs Insights to query these events for dashboards and operational visibility.
