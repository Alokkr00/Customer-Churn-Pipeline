variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name identifier for resource tagging"
  type        = string
  default     = "customer-churn"
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for DB subnet group"
  type        = list(string)
}

variable "rds_security_group_id" {
  description = "Security group ID for RDS PostgreSQL"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "churn_db"
}

variable "db_user" {
  description = "Master username for PostgreSQL"
  type        = string
  default     = "churn_admin"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}
