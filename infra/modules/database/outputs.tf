output "db_endpoint" {
  description = "The database connection endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
}

output "db_address" {
  description = "The database host address"
  value       = aws_db_instance.postgres.address
}

output "db_port" {
  description = "The database port"
  value       = aws_db_instance.postgres.port
}

output "db_name" {
  description = "The database name"
  value       = aws_db_instance.postgres.db_name
}

output "db_secret_arn" {
  description = "The ARN of Secrets Manager secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}
