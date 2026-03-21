resource "aws_iam_role" "this" {
  name               = var.role_name
  description        = var.role_description
  assume_role_policy = var.trust_policy_json
  tags               = var.tags
}

resource "aws_iam_role_policy" "this" {
  name   = "${var.role_name}-policy"
  role   = aws_iam_role.this.id
  policy = var.role_policy_json
}