# ==============================================================================
# Oracle Cloud Infrastructure (OCI) Variables
# ==============================================================================

variable "tenancy_ocid" {
  description = "The OCID of the OCI Tenancy"
  type        = string
}

variable "user_ocid" {
  description = "The OCID of the OCI User with permission to manage resources"
  type        = string
}

variable "compartment_ocid" {
  description = "The OCID of the Compartment where resources will be created"
  type        = string
}

variable "fingerprint" {
  description = "Fingerprint of the RSA public key uploaded to the OCI user"
  type        = string
}

variable "private_key_path" {
  description = "Path to the private key file corresponding to the uploaded public key"
  type        = string
}

variable "region" {
  description = "OCI Region identifier (e.g. us-ashburn-1, us-phoenix-1, ap-mumbai-1, eu-frankfurt-1)"
  type        = string
  default     = "us-ashburn-1"
}

variable "ssh_public_key" {
  description = "Public SSH key content (e.g. ssh-ed25519 ... or ssh-rsa ...) for instance access"
  type        = string
}

variable "instance_shape" {
  description = "Compute instance shape. Default is Always Free Ampere A1 ARM64."
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "ocpus" {
  description = "Number of OCPUs for flexible shapes (Ampere A1 supports up to 4 OCPUs free)"
  type        = number
  default     = 4
}

variable "memory_in_gbs" {
  description = "RAM in GBs for flexible shapes (Ampere A1 supports up to 24 GB free)"
  type        = number
  default     = 24
}

variable "boot_volume_size_in_gbs" {
  description = "Size of the boot volume in GB (Always Free allows up to 200 GB total)"
  type        = number
  default     = 100
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}
