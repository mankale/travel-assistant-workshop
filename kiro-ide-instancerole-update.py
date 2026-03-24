"""
Finds the Kiro IDE instance role (kiro-ide-remote-InstanceRole-*) and ensures
all policies required by the travel-assistant workshop scripts are attached.
"""

import json
import boto3

iam = boto3.client("iam")

POLICY_NAME = "TravelAssistantWorkshopPolicy"

POLICY_DOCUMENT = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "IAMRoleManagement",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole", "iam:DeleteRole",
                "iam:PutRolePolicy", "iam:DeleteRolePolicy",
                "iam:AttachRolePolicy", "iam:DetachRolePolicy",
                "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
                "iam:GetRole", "iam:PassRole",
            ],
            "Resource": "*",
        },
        {
            "Sid": "Lambda",
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction", "lambda:GetFunction",
                "lambda:InvokeFunction", "lambda:UpdateFunctionCode",
            ],
            "Resource": "*",
        },
        {
            "Sid": "Cognito",
            "Effect": "Allow",
            "Action": "cognito-idp:*",
            "Resource": "*",
        },
        {
            "Sid": "BedrockAgentCore",
            "Effect": "Allow",
            "Action": "bedrock-agentcore:*",
            "Resource": "*",
        },
        {
            "Sid": "SSM",
            "Effect": "Allow",
            "Action": ["ssm:PutParameter", "ssm:GetParameter"],
            "Resource": "*",
        },
        {
            "Sid": "ECR",
            "Effect": "Allow",
            "Action": "ecr:*",
            "Resource": "*",
        },
        {
            "Sid": "CodeBuild",
            "Effect": "Allow",
            "Action": "codebuild:*",
            "Resource": "*",
        },
        {
            "Sid": "S3ForCodeBuild",
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*",
        },
        {
            "Sid": "Logs",
            "Effect": "Allow",
            "Action": "logs:*",
            "Resource": "*",
        },
    ],
})


def find_instance_role():
    paginator = iam.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page["Roles"]:
            if role["RoleName"].startswith("kiro-ide-remote-InstanceRole-"):
                return role["RoleName"]
    return None


def policy_already_attached(role_name):
    for p in iam.list_role_policies(RoleName=role_name)["PolicyNames"]:
        if p == POLICY_NAME:
            return True
    return False


def main():
    role_name = find_instance_role()
    if not role_name:
        print("❌ No role matching 'kiro-ide-remote-InstanceRole-*' found.")
        return

    print(f"Found instance role: {role_name}")

    if policy_already_attached(role_name):
        print(f"✅ Policy '{POLICY_NAME}' already attached — no changes needed.")
        return

    iam.put_role_policy(RoleName=role_name, PolicyName=POLICY_NAME, PolicyDocument=POLICY_DOCUMENT)
    print(f"✅ Attached '{POLICY_NAME}' to {role_name}")


if __name__ == "__main__":
    main()
