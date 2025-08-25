variable "project_name" {
  type    = string
  default = "fraud-inference"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "ecr_repo_name" {
  type    = string
  default = "fraud-inference-repo"
}

variable "image_tag" {
  type    = string
  default = "latest"
}
