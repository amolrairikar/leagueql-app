terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

provider "aws" {
  alias  = "replica"
  region = "us-west-2"
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  providers = {
    aws.primary = aws.primary
    aws.replica = aws.replica
  }

  table_name      = "fantasy-football-recap-table-dev"
  hash_key        = "PK"
  range_key       = "SK"
  replica_regions = ["us-west-2"]
  
  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "database"
    managed-by  = "terraform"
  }
}