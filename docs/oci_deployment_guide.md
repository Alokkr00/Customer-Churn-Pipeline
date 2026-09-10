# ☁️ Oracle Cloud Infrastructure (OCI) Deployment Guide

A complete, production-grade guide to deploying the **Customer Churn Prediction & Retention MLOps Pipeline** on **Oracle Cloud Infrastructure (OCI)**.

This guide leverages **OCI Always Free Tier**, enabling you to host the entire end-to-end pipeline—including PostgreSQL, MinIO, MLflow, Apache Airflow, FastAPI Serving, and Streamlit Hub—**100% free forever** with zero cloud bills.

---

## 📑 Table of Contents
- [Why Oracle Cloud Always Free?](#why-oracle-cloud-always-free)
- [Architecture Overview](#architecture-overview)
- [Option 1: Interactive Console Setup (Recommended)](#option-1-interactive-console-setup-recommended)
  - [Step 1: Create Virtual Cloud Network (VCN)](#step-1-create-virtual-cloud-network-vcn)
  - [Step 2: Configure VCN Ingress Rules](#step-2-configure-vcn-ingress-rules)
  - [Step 3: Provision Compute Instance (Ampere A1)](#step-3-provision-compute-instance-ampere-a1)
  - [Step 4: Connect via SSH & Run Host Bootstrap](#step-4-connect-via-ssh--run-host-bootstrap)
  - [Step 5: Clone Repo & Launch Pipeline](#step-5-clone-repo--launch-pipeline)
- [Option 2: Automated Terraform IaC Deployment](#option-2-automated-terraform-iac-deployment)
- [Solving the OCI "Double Firewall" Gotcha](#solving-the-oci-double-firewall-gotcha)
- [Production Domain & Free SSL (Caddy Reverse Proxy)](#production-domain--free-ssl-caddy-reverse-proxy)
- [Operations & Monitoring Checklist](#operations--monitoring-checklist)

---

## Why Oracle Cloud Always Free?

Unlike AWS or Azure which offer 12-month limited trials, Oracle Cloud offers a generous **Always Free Tier** that never expires:

| Resource | Always Free Allowance | How We Use It |
|---|---|---|
| **Ampere A1 Compute (ARM64)** | **4 OCPUs & 24 GB RAM** | Runs the entire pipeline concurrently with zero throttling. |
| **AMD Compute (x86_64)** | 2 Micro instances (1 GB RAM each) | Optional lightweight edge proxies or bastion hosts. |
| **Block Storage** | **200 GB NVMe** | 100 GB OS & Docker storage, database persistence. |
| **Outbound Data Transfer** | **10 TB / month** | Ample bandwidth for inference APIs and dashboards. |
| **Cost** | **$0.00 / month forever** | 100% free production portfolio hosting. |

---

## Architecture Overview

```text
Internet / Users
       │
       ▼ (Ports 80/443 or Direct Application Ports)
┌─────────────────────────────────────────────────────────────┐
│ OCI Virtual Cloud Network (VCN: 10.0.0.0/16)                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ OCI Ampere A1 Instance (4 OCPU / 24 GB RAM)           │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │ Docker Engine & Docker Compose Network          │  │  │
│  │  │                                                 │  │  │
│  │  │  • FastAPI Service       (:8000) ◄── Inference  │  │  │
│  │  │  • Streamlit Hub         (:8501) ◄── UI Portal  │  │  │
│  │  │  • MLflow Server         (:5000) ◄── Registry   │  │  │
│  │  │  • Airflow Webserver     (:8080) ◄── DAG Runs   │  │  │
│  │  │  • PostgreSQL 15         (:5432) ◄── Data Mart  │  │  │
│  │  │  • MinIO S3              (:9000) ◄── Artifacts  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Option 1: Interactive Console Setup (Recommended)

### Step 1: Create Virtual Cloud Network (VCN)
1. Log into your [Oracle Cloud Console](https://cloud.oracle.com/).
2. Open the navigation menu (`☰`) -> **Networking** -> **Virtual Cloud Networks**.
3. Click **Start VCN Wizard** -> Select **Create VCN with Internet Connectivity** -> Click **Start VCN Wizard**.
4. Set:
   - **VCN Name**: `churn-pipeline-vcn`
   - **Compartment**: Select your compartment (or root).
5. Click **Next** -> Click **Create**.

---

### Step 2: Configure VCN Ingress Rules
By default, OCI allows port 22 (SSH). We must allow application traffic:
1. Under **Virtual Cloud Networks**, click on your newly created `churn-pipeline-vcn`.
2. Under **Subnets**, click on the **Public Subnet**.
3. Under **Security Lists**, click **Default Security List for churn-pipeline-vcn**.
4. Click **Add Ingress Rules** and add the following rules:

| Source CIDR | IP Protocol | Destination Port Range | Description |
|---|---|---|---|
| `0.0.0.0/0` | TCP | `80` | HTTP / ACME SSL Challenge |
| `0.0.0.0/0` | TCP | `443` | HTTPS Secure Web |
| `0.0.0.0/0` | TCP | `8000` | FastAPI Real-time Serving & Docs |
| `0.0.0.0/0` | TCP | `8501` | Streamlit Customer Retention Hub |
| `0.0.0.0/0` | TCP | `5000` | MLflow Experiment Tracking UI |
| `0.0.0.0/0` | TCP | `8080` | Apache Airflow Webserver |

5. Click **Add Ingress Rules**.

---

### Step 3: Provision Compute Instance (Ampere A1)
1. Open navigation menu (`☰`) -> **Compute** -> **Instances**.
2. Click **Create Instance**.
3. Configure the instance:
   - **Name**: `churn-mlops-server`
   - **Image**: Click **Change image** -> Select **Canonical Ubuntu** -> Choose **Ubuntu 22.04 Minimal** or **Ubuntu 22.04 LTS**.
   - **Shape**: Click **Change shape**:
     - Select **Ampere** (Arm-based processor).
     - Choose **VM.Standard.A1.Flex** (Always Free Eligible).
     - Move sliders to **4 OCPU** and **24 GB Memory**.
   - **Networking**: Select your `churn-pipeline-vcn` and **Public Subnet**. Ensure **Assign a public IPv4 address** is checked.
   - **Add SSH keys**: Select **Generate a key pair for me** (and download both Private and Public keys) OR paste your existing public SSH key (`~/.ssh/id_ed25519.pub`).
   - **Boot volume**: Check **Specify a custom boot volume size** and set to **100 GB** (well within the 200 GB free limit).
4. Click **Create**. Wait 1–2 minutes until the instance state changes to **Running**.
5. Copy the **Public IP Address** displayed on the instance details page.

> [!TIP]
> **Out of Host Capacity?**: If Ampere A1 reports "Out of host capacity" in your home region, try changing the **Availability Domain** (AD-1, AD-2, or AD-3), or provision an Always Free **VM.Standard.E2.1.Micro** instance.

---

### Step 4: Connect via SSH & Run Host Bootstrap
Open your local terminal and connect to your instance:

```bash
# Connect using the downloaded private key
ssh -i /path/to/ssh-key.key ubuntu@<YOUR_OCI_PUBLIC_IP>
```

Run our automated bootstrap script directly from the repository. This installs Docker, Docker Compose, Git, and **unblocks the OCI OS-level firewall**:

```bash
curl -fsSL https://raw.githubusercontent.com/Alokkr00/Customer-Churn-Pipeline/main/scripts/oci_setup.sh | bash
```

Activate docker permissions without logging out:
```bash
newgrp docker
```

---

### Step 5: Clone Repo & Launch Pipeline

Clone your repository:
```bash
git clone https://github.com/Alokkr00/Customer-Churn-Pipeline.git
cd Customer-Churn-Pipeline
```

Launch the complete production stack (Postgres, MinIO, MLflow, Airflow, FastAPI, and Streamlit):
```bash
docker compose -f docker-compose.prod.yml up -d
```

Check container status:
```bash
docker compose -f docker-compose.prod.yml ps
```

Your services are now live on the internet:
- 📡 **FastAPI Documentation & Inference**: `http://<YOUR_OCI_PUBLIC_IP>:8000/docs`
- 🎯 **Streamlit Customer Retention Hub**: `http://<YOUR_OCI_PUBLIC_IP>:8501`
- 🔬 **MLflow Tracking Server**: `http://<YOUR_OCI_PUBLIC_IP>:5000`
- 🌪️ **Apache Airflow Orchestrator**: `http://<YOUR_OCI_PUBLIC_IP>:8080` (Login: `admin` / `admin`)

---

## Option 2: Automated Terraform IaC Deployment

If you prefer Infrastructure-as-Code automation, use the pre-built Terraform module under [`infra/oci/`](../infra/oci/):

### 1. Prerequisites
- [Terraform >= 1.5.0](https://www.terraform.io/)
- OCI API Signing Key generated in your OCI Profile (**Profile** -> **API Keys** -> **Add API Key**).

### 2. Configure Credentials
```bash
cd infra/oci
cp terraform.tfvars.example terraform.tfvars
```

Fill in your OCI OCIDs in `terraform.tfvars`:
```hcl
tenancy_ocid     = "ocid1.tenancy.oc1..aaaa..."
user_ocid        = "ocid1.user.oc1..aaaa..."
compartment_ocid = "ocid1.compartment.oc1..aaaa..."
fingerprint      = "12:34:56:78:..."
private_key_path = "~/.oci/oci_api_key.pem"
region           = "us-ashburn-1"
ssh_public_key   = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5... user@host"
```

### 3. Deploy
```bash
terraform init
terraform plan
terraform apply -auto-approve
```

Terraform automatically outputs your server IP and direct access URLs:
```text
Outputs:
fastapi_api_url     = "http://129.153.x.x:8000/docs"
instance_public_ip  = "129.153.x.x"
mlflow_tracking_url = "http://129.153.x.x:5000"
ssh_command         = "ssh -i <key> ubuntu@129.153.x.x"
streamlit_hub_url   = "http://129.153.x.x:8501"
```

---

## Solving the OCI "Double Firewall" Gotcha

> [!WARNING]
> **Why Can't I Connect Even Though OCI Security Lists Allow Port 8000 / 8501?**
>
> Unlike AWS (where Security Groups are the only firewall), Oracle Cloud images include a pre-configured host OS firewall via `iptables` that **drops all non-port-22 incoming traffic by default**!
>
> If you set up an instance manually without our bootstrap script, run this command on the server to unblock all required ports:
>
> ```bash
> sudo iptables -I INPUT 6 -p tcp -m multiport --dports 80,443,8000,8501,5000,8080 -j ACCEPT
> sudo netfilter-persistent save
> ```

---

## Production Domain & Free SSL (Caddy Reverse Proxy)

For a clean portfolio URL with automatic Let's Encrypt HTTPS (e.g. `churn.yourdomain.com` or a free DuckDNS domain):

1. Point your domain DNS `A` record to `<YOUR_OCI_PUBLIC_IP>`.
2. Install Caddy on the OCI instance:
   ```bash
   sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
   curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
   sudo apt-get update && sudo apt-get install -y caddy
   ```
3. Edit `/etc/caddy/Caddyfile`:
   ```caddyfile
   churn.yourdomain.com {
       # Route API traffic to FastAPI
       handle_path /api/* {
           reverse_proxy localhost:8000
       }

       # Route web traffic to Streamlit Retention Hub
       handle {
           reverse_proxy localhost:8501
       }
   }
   ```
4. Reload Caddy:
   ```bash
   sudo systemctl reload caddy
   ```

Caddy automatically provisions and renews SSL certificates from Let's Encrypt for free.

---

## Operations & Monitoring Checklist

- **Check Container Logs**:
  ```bash
  docker compose -f docker-compose.prod.yml logs -f serving
  docker compose -f docker-compose.prod.yml logs -f streamlit
  ```
- **Retrigger Daily Batch Scoring DAG**:
  ```bash
  docker compose -f docker-compose.prod.yml exec airflow-webserver airflow dags trigger daily_scoring
  ```
- **Restart All Services**:
  ```bash
  docker compose -f docker-compose.prod.yml restart
  ```
- **Clean Teardown**:
  ```bash
  docker compose -f docker-compose.prod.yml down
  ```
