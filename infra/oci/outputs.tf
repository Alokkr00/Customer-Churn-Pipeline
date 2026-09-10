# ==============================================================================
# OCI Deployment Outputs
# ==============================================================================

output "instance_public_ip" {
  description = "Public IP address assigned to the OCI compute instance"
  value       = oci_core_instance.churn_server.public_ip
}

output "ssh_command" {
  description = "Convenience SSH command to connect to the compute instance"
  value       = "ssh -i <path-to-private-key> ubuntu@${oci_core_instance.churn_server.public_ip}"
}

output "fastapi_api_url" {
  description = "FastAPI Swagger documentation and real-time prediction endpoint"
  value       = "http://${oci_core_instance.churn_server.public_ip}:8000/docs"
}

output "streamlit_hub_url" {
  description = "Streamlit Customer Retention Hub and What-If Simulator"
  value       = "http://${oci_core_instance.churn_server.public_ip}:8501"
}

output "mlflow_tracking_url" {
  description = "MLflow Experiment Tracking and Model Registry"
  value       = "http://${oci_core_instance.churn_server.public_ip}:5000"
}

output "airflow_ui_url" {
  description = "Apache Airflow scheduled scoring orchestration UI"
  value       = "http://${oci_core_instance.churn_server.public_ip}:8080"
}
