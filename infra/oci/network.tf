# ==============================================================================
# OCI Virtual Cloud Network (VCN), Subnets, and Security Lists
# ==============================================================================

resource "oci_core_vcn" "churn_vcn" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "churn-vcn-${var.environment}"
  dns_label      = "churnvcn"
}

resource "oci_core_internet_gateway" "churn_igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.churn_vcn.id
  display_name   = "churn-igw-${var.environment}"
  enabled        = true
}

resource "oci_core_default_route_table" "churn_route_table" {
  manage_default_resource_id = oci_core_vcn.churn_vcn.default_route_table_id

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.churn_igw.id
  }
}

resource "oci_core_security_list" "churn_security_list" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.churn_vcn.id
  display_name   = "churn-sec-list-${var.environment}"

  # Allow all outbound traffic
  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
    description = "Allow all outbound traffic"
  }

  # Ingress: SSH (Port 22)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "SSH administrative access"

    tcp_options {
      min = 22
      max = 22
    }
  }

  # Ingress: HTTP (Port 80)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "HTTP web traffic / ACME Let's Encrypt validation"

    tcp_options {
      min = 80
      max = 80
    }
  }

  # Ingress: HTTPS (Port 443)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "HTTPS encrypted web traffic"

    tcp_options {
      min = 443
      max = 443
    }
  }

  # Ingress: FastAPI Real-Time Serving (Port 8000)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "FastAPI churn inference endpoints and Swagger docs"

    tcp_options {
      min = 8000
      max = 8000
    }
  }

  # Ingress: Streamlit Retention Hub (Port 8501)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "Streamlit Customer Retention Hub and Simulator"

    tcp_options {
      min = 8501
      max = 8501
    }
  }

  # Ingress: MLflow Tracking UI (Port 5000)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "MLflow Experiment Tracking and Model Registry"

    tcp_options {
      min = 5000
      max = 5000
    }
  }

  # Ingress: Apache Airflow Webserver (Port 8080)
  ingress_security_rules {
    protocol    = "6"
    source      = "0.0.0.0/0"
    description = "Apache Airflow UI for batch scoring DAGs"

    tcp_options {
      min = 8080
      max = 8080
    }
  }
}

resource "oci_core_subnet" "churn_public_subnet" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.churn_vcn.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "churn-public-subnet-${var.environment}"
  dns_label         = "churnpublic"
  security_list_ids = [oci_core_security_list.churn_security_list.id]
  route_table_id    = oci_core_default_route_table.churn_route_table.id
}
