# Create the log group explicitly to manage retention
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention
  tags              = var.tags
}

# Data source to get information about the S3 object (the zip file)
data "aws_s3_object" "lambda_package" {
  bucket = var.s3_bucket
  key    = var.s3_key
}

locals {
  # Prefer version_id (stable, requires bucket versioning) and fall back to etag.
  # Either changes whenever a new artifact is uploaded, triggering redeployment.
  source_code_hash = coalesce(
    data.aws_s3_object.lambda_package.version_id,
    data.aws_s3_object.lambda_package.etag
  )
}

resource "aws_lambda_function" "this" {
  function_name     = var.function_name
  description       = var.function_description
  role              = var.role_arn
  handler           = var.handler
  layers            = var.layers
  memory_size       = var.memory_size
  timeout           = var.timeout
  s3_bucket         = var.s3_bucket
  s3_key            = var.s3_key
  s3_object_version = data.aws_s3_object.lambda_package.version_id
  runtime           = "python3.13"

  environment {
    variables = var.environment_variables
  }

  tags       = var.tags
  depends_on = [aws_cloudwatch_log_group.lambda_log_group]
}