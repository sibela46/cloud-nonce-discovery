There are two ways to run the program. The first one involves direct specification for the number of instances to be created, and the second one is indirect (a desired run time is required instead). To run:

1) Direct specification
    python main.py D no I
where D is the difficulty value, yes stands for "direct specification", I is the number of instances

2) Indirect specification
    python main.py D yes T
where D is the difficulty value, no stands for "indirect specification", T is the run time for nonce discovery

Note that in the second case the selected run time encapsulates the nonce discovery only. Time spent initialising and shutting down the virtual machines is separate and is usually around ~70-80 seconds.

To run this you need to create a User that has AdministratorAccess permissions, and an IAM role with the same permissions. After that you need the user's AWS access and secret keys, an instance profile ARN for you IAM role and a S3 bucket name, all stored in a .env file like so:

AWS_ACCESS=your_aws_access_key_here
AWS_SECRET=your_aws_secret_key_here
ROLE_ARN=instance_profile_arn_of_your_iam_role
BUCKET_NAME=your_bucket_name