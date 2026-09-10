resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket        = "${var.project_name}-${var.environment}-mlflow-${random_id.bucket_suffix.hex}"
  force_destroy = var.environment == "dev" ? true : false

  tags = {
    Name        = "${var.project_name}-${var.environment}-mlflow-artifacts"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "public_block" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
