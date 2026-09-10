variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "customer-churn"
}

variable "container_image" {
  description = "GHCR Docker image URI"
  type        = string
  default     = "ghcr.io/alokkr00/customer-churn-pipeline/serving:latest"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "container_cpu" {
  description = "Fargate CPU units"
  type        = number
  default     = 256
}

variable "container_memory" {
  description = "Fargate Memory in MB"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of running containers"
  type        = number
  default     = 1
}
