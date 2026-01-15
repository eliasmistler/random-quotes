output "ecr_backend_url" {
  description = "ECR repository URL for backend image"
  value       = module.ecr.backend_repository_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for frontend image"
  value       = module.ecr.frontend_repository_url
}

output "alb_dns_name" {
  description = "ALB DNS name (your application URL)"
  value       = module.ecs.alb_dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions (use as AWS_ROLE_ARN secret)"
  value       = aws_iam_role.github_actions.arn
}
