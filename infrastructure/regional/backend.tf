# The S3 bucket containing state has the AWS account number in the file
# To prevent committing this to git, define the backend config in a
# backend.hcl file and add that file to .gitignore
terraform {
  backend "s3" {}
}