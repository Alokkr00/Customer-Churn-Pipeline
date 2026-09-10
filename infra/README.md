# ☁️ Cloud Infrastructure (Terraform IaC)

Production-grade Infrastructure-as-Code (IaC) configuration for deploying the Customer Churn Prediction and Retention MLOps pipeline to **Amazon Web Services (AWS)**.

---

## 🏗️ Cloud Architecture

```
Internet
   │
   ▼
[ Application Load Balancer (ALB) ] (Public Subnets: 10.0.1.0/24, 10.0.2.0/24)
   │
   │  Port 8000
   ▼
[ ECS Fargate Cluster ] (Private Subnets: 10.0.10.0/24, 10.0.20.0/24)
   │  Container: ghcr.io/alokkr00/customer-churn-pipeline/serving:latest
   │  Auto-scaling: Target Tracking on 70% CPU (1 - 5 tasks)
   │
   ├──► [ Amazon S3 ] (MLflow Model Artifacts Bucket with AES256 Encryption)
   └──► [ Amazon RDS PostgreSQL 15 ] (Private Subnets, Port 5432)
```

---

## 📂 Module Breakdown

| Module | Resources Provisioned |
|---|---|
| **`modules/networking`** | VPC (`10.0.0.0/16`), 2 Public Subnets, 2 Private Subnets, Internet Gateway, NAT Gateway, Elastic IP, Route Tables, and 3 Security Groups (ALB, ECS, RDS). |
| **`modules/storage`** | S3 bucket for MLflow models and artifacts, bucket versioning, server-side AES256 encryption, and S3 public access block. |
| **`modules/database`** | AWS Secrets Manager secret for DB master credentials, DB Subnet Group, and Amazon RDS PostgreSQL 15 (`gp3` storage, multi-AZ optional). |
| **`modules/serving`** | CloudWatch Log Group, ECS Cluster, IAM Task & Execution Roles, Fargate Task Definition (GHCR container), Application Load Balancer (ALB), Target Group with `/health` checks, and Target Tracking Auto Scaling. |

---

## 🏢 Multi-Environment Strategy

| Environment | RDS Instance Class | Multi-AZ | Fargate Task Size | Task Replicas | Est. Monthly Cost |
|---|---|---|---|---|---|
| **Dev** | `db.t3.micro` | Disabled | 0.25 vCPU / 512 MB | 1 (min 1, max 2) | ~$18 - $28 |
| **Prod** | `db.t3.small` | Enabled | 0.50 vCPU / 1024 MB | 2 (min 2, max 5) | ~$65 - $95 |

---

## 🚀 Deployment Instructions

### Prerequisites
- [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) >= 1.5.0
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials (`aws configure`)

### 1. Initialize & Validate (Dev)
```bash
cd infra/environments/dev

# Initialize Terraform providers (AWS ~> 5.0, Random ~> 3.5)
terraform init

# Validate configuration syntax
terraform validate

# Review proposed changes
terraform plan
```

### 2. Deploy Infrastructure
```bash
terraform apply -auto-approve
```
After deployment completes, Terraform outputs the public API endpoint:
```text
Outputs:
api_endpoint = "http://customer-churn-dev-alb-123456789.us-east-1.elb.amazonaws.com"
alb_dns_name = "customer-churn-dev-alb-123456789.us-east-1.elb.amazonaws.com"
db_endpoint  = "customer-churn-dev-db.xxxxxx.us-east-1.rds.amazonaws.com:5432"
s3_artifact_bucket = "customer-churn-dev-mlflow-a1b2c3d4"
```

### 3. Verify Live Prediction Service
```bash
# Verify health probe
curl http://<ALB_DNS_NAME>/health

# Run sample churn risk inference
curl -X POST "http://<ALB_DNS_NAME>/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "customer_id": "CLOUD-TEST-001",
       "tenure_months": 2,
       "contract_type": "Month-to-month",
       "internet_service": "Fiber optic",
       "monthly_charges": 85.50
     }'
```

### 4. Teardown (Cost Management)
When finished testing or presenting a portfolio demo, destroy resources to avoid ongoing AWS charges:
```bash
terraform destroy -auto-approve
```
