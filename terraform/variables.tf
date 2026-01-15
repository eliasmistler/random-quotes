variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ransom-notes"
}

variable "environment" {
  description = "Environment name (e.g., prod, staging)"
  type        = string
  default     = "prod"
}

variable "github_repo" {
  description = "GitHub repository in format 'owner/repo' for OIDC trust"
  type        = string
}

variable "backend_cpu" {
  description = "CPU units for backend task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "backend_memory" {
  description = "Memory in MB for backend task"
  type        = number
  default     = 512
}

variable "frontend_cpu" {
  description = "CPU units for frontend task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Memory in MB for frontend task"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of tasks per service"
  type        = number
  default     = 1
}
