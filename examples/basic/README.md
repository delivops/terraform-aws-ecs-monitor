# Basic ECS Crash Monitor Example

This example shows the basic usage of the ECS Crash Monitor module with only CloudWatch logging enabled.

## Usage

```bash
terraform init
terraform plan
terraform apply
```

## Configuration

Update the `terraform.tfvars` file with your specific values before applying.

## Outputs

After applying, you can view crash events in CloudWatch Logs at:
- Log Group: `/aws/ecs/monitoring/{cluster_name}/crash-events`