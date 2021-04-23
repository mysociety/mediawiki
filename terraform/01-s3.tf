resource "aws_s3_bucket" "wiki_resources" {
  bucket = "ms-wr-${var.bucket_domain_name}"
  versioning {
    enabled = true
  }
  lifecycle_rule {
    id      = "version_expiry"
    enabled = true
    noncurrent_version_expiration {
      days = var.expire_version_days
    }
  }
  lifecycle {
    prevent_destroy = true
  }
  tags = {
    Name      = "Wiki Resources for ${var.bucket_domain_name}"
    Terraform = "true"
  }
}

resource "aws_iam_user_policy" "wiki_resources_user_policy" {
  name       = "${var.bucket_domain_name}-user-policy"
  user       = var.wiki_user
  depends_on = [aws_s3_bucket.wiki_resources]
  policy     = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowAllS3ActionsFor${var.wiki_user}",
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::ms-wr-${var.bucket_domain_name}/*"
            ]
        },
        {
            "Sid": "AllowReadingFor${var.wiki_user}",
            "Effect": "Allow",
            "Action": [
                "s3:Get*",
                "s3:List*"
            ],
            "Resource": [
                "arn:aws:s3:::ms-wr-${var.bucket_domain_name}"
            ]
        }
    ]
}
EOF

}

