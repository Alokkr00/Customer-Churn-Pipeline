aws_region        = "us-east-1"
environment       = "dev"
project_name      = "customer-churn"
container_image   = "ghcr.io/alokkr00/customer-churn-pipeline/serving:latest"
db_instance_class = "db.t3.micro"
container_cpu     = 256
container_memory  = 512
desired_count     = 1
