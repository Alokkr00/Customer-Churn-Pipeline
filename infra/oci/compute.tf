# ==============================================================================
# OCI Compute Instance (Always Free Ampere A1 or AMD Micro)
# ==============================================================================

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "churn_server" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "churn-mlops-server-${var.environment}"
  shape               = var.instance_shape

  dynamic "shape_config" {
    for_each = length(regexall("Flex", var.instance_shape)) > 0 ? [1] : []
    content {
      ocpus         = var.ocpus
      memory_in_gbs = var.memory_in_gbs
    }
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.churn_public_subnet.id
    display_name     = "primary-vnic"
    assign_public_ip = true
    hostname_label   = "churnserver"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(<<-EOF
      #!/bin/bash
      set -euxo pipefail

      # Update apt
      apt-get update -y
      DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl gnupg lsb-release git make iptables-persistent netfilter-persistent

      # Docker installation
      install -m 0755 -d /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      chmod a+r /etc/apt/keyrings/docker.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
      apt-get update -y
      DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

      # Add ubuntu user to docker group
      usermod -aG docker ubuntu

      # Unblock OCI host-level iptables rules for application ports
      for port in 80 443 8000 8501 5000 8080; do
        iptables -I INPUT 6 -p tcp --dport $port -m state --state NEW,ESTABLISHED -j ACCEPT
      done
      netfilter-persistent save

      systemctl enable docker
      systemctl start docker
      echo "OCI Host Bootstrap complete" > /var/log/oci_bootstrap.done
    EOF
    )
  }
}
