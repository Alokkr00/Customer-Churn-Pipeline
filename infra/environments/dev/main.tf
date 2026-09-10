terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

module "networking" {
  source       = "../../modules/networking"
  environment  = var.environment
  project_name = var.project_name
}

module "storage" {
  source       = "../../modules/storage"
  environment  = var.environment
  project_name = var.project_name
}

module "database" {
  source                = "../../modules/database"
  environment           = var.environment
  project_name          = var.project_name
  private_subnet_ids    = module.networking.private_subnet_ids
  rds_security_group_id = module.networking.rds_security_group_id
  db_instance_class     = var.db_instance_class
  multi_az              = false
}

module "serving" {
  source                      = "../../modules/serving"
  environment                 = var.environment
  project_name                = var.project_name
  vpc_id                      = module.networking.vpc_id
  public_subnet_ids           = module.networking.public_subnet_ids
  private_subnet_ids          = module.networking.private_subnet_ids
  alb_security_group_id       = module.networking.alb_security_group_id
  ecs_tasks_security_group_id = module.networking.ecs_tasks_security_group_id
  container_image             = var.container_image
  container_cpu               = var.container_cpu
  container_memory            = var.container_memory
  desired_count               = var.desired_count
  min_count                   = 1
  max_count                   = 2
  db_address                  = module.database.db_address
  db_port                     = module.database.db_port
  db_name                     = module.database.db_name
  db_secret_arn               = module.database.db_secret_arn
  s3_bucket_arn               = module.storage.bucket_arn
  s3_bucket_id                = module.storage.bucket_id
}
