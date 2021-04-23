terraform {
  backend "s3" {
  }
}

variable "aws_region" {
  description = "AWS region to hold the resources"
  default     = "eu-west-1"
}

variable "wiki_user" {
  description = "IAM username for accessing AWS resources"
  default     = "wiki"
}

variable "bucket_domain_name" {
  description = "Suffix for the name of the bucket for the Uploads. Will be prefixed with ms-wr-."
  default     = "wiki-mysociety-org"
}

variable "expire_version_days" {
  description = "Number of days before versions expire from the bucket"
  default     = 28
}

provider "aws" {
  region = var.aws_region
}

