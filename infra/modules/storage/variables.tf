variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name identifier for resource tagging"
  type        = string
  default     = "customer-churn"
}
