variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name identifier for resource tagging"
  type        = string
  default     = "customer-churn"
}

variable "vpc_id" {
  description = "VPC ID where serving components will be deployed"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the ECS Fargate tasks"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for the ALB"
  type        = string
}

variable "ecs_tasks_security_group_id" {
  description = "Security group ID for ECS Fargate tasks"
  type        = string
}

variable "container_image" {
  description = "Docker container image URI from GHCR"
  type        = string
  default     = "ghcr.io/alokkr00/customer-churn-pipeline/serving:latest"
}

variable "container_cpu" {
  description = "Fargate CPU units (256 = 0.25 vCPU, 512 = 0.5 vCPU, 1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "container_memory" {
  description = "Fargate memory in MB (512, 1024, 2048)"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of running ECS tasks"
  type        = number
  default     = 1
}

variable "min_count" {
  description = "Minimum number of running ECS tasks for autoscaling"
  type        = number
  default     = 1
}

variable "max_count" {
  description = "Maximum number of running ECS tasks for autoscaling"
  type        = number
  default     = 3
}

variable "db_address" {
  description = "PostgreSQL DB host address"
  type        = string
}

variable "db_port" {
  description = "PostgreSQL DB port"
  type        = number
}

variable "db_name" {
  description = "PostgreSQL DB name"
  type        = string
}

variable "db_secret_arn" {
  description = "ARN of Secrets Manager secret containing database credentials"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of MLflow S3 artifact bucket"
  type        = string
}

variable "s3_bucket_id" {
  description = "ID/Name of MLflow S3 artifact bucket"
  type        = string
}
