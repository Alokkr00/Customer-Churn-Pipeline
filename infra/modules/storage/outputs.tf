output "bucket_id" {
  description = "The name/ID of the MLflow S3 bucket"
  value       = aws_s3_bucket.mlflow_artifacts.id
}

output "bucket_arn" {
  description = "The ARN of the MLflow S3 bucket"
  value       = aws_s3_bucket.mlflow_artifacts.arn
}
