aws_region        = "us-east-1"
environment       = "prod"
project_name      = "customer-churn"
container_image   = "ghcr.io/alokkr00/customer-churn-pipeline/serving:latest"
db_instance_class = "db.t3.small"
container_cpu     = 512
container_memory  = 1024
desired_count     = 2
