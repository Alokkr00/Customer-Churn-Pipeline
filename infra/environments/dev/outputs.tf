output "api_endpoint" {
  description = "Public URL for FastAPI Churn Prediction Service"
  value       = module.serving.api_endpoint
}

output "alb_dns_name" {
  description = "DNS name of the ALB"
  value       = module.serving.alb_dns_name
}

output "db_endpoint" {
  description = "PostgreSQL DB connection endpoint"
  value       = module.database.db_endpoint
}

output "s3_artifact_bucket" {
  description = "S3 bucket for MLflow models and artifacts"
  value       = module.storage.bucket_id
}
