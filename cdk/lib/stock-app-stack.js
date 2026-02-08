"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.StockAppStack = void 0;
const cdk = require("aws-cdk-lib");
const ec2 = require("aws-cdk-lib/aws-ec2");
const elbv2 = require("aws-cdk-lib/aws-elasticloadbalancingv2");
const targets = require("aws-cdk-lib/aws-elasticloadbalancingv2-targets");
const cloudfront = require("aws-cdk-lib/aws-cloudfront");
const origins = require("aws-cdk-lib/aws-cloudfront-origins");
const iam = require("aws-cdk-lib/aws-iam");
class StockAppStack extends cdk.Stack {
    constructor(scope, id, props) {
        super(scope, id, props);
        // VPC
        const vpc = new ec2.Vpc(this, 'StockAppVpc', {
            maxAzs: 2,
            natGateways: 1,
        });
        // Security Group for ALB
        const albSg = new ec2.SecurityGroup(this, 'AlbSecurityGroup', {
            vpc,
            description: 'Security group for ALB',
            allowAllOutbound: true,
        });
        albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow HTTP');
        // Security Group for EC2
        const ec2Sg = new ec2.SecurityGroup(this, 'Ec2SecurityGroup', {
            vpc,
            description: 'Security group for EC2',
            allowAllOutbound: true,
        });
        ec2Sg.addIngressRule(albSg, ec2.Port.tcp(8501), 'Allow Streamlit from ALB');
        // IAM Role for EC2
        const ec2Role = new iam.Role(this, 'Ec2Role', {
            assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
                iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonBedrockFullAccess'),
            ],
        });
        // S3 access for deployment
        ec2Role.addToPolicy(new iam.PolicyStatement({
            actions: ['s3:GetObject'],
            resources: ['arn:aws:s3:::stock-ai-agent-deploy-1770486416/*'],
        }));
        // User Data for EC2
        const userData = ec2.UserData.forLinux();
        userData.addCommands('yum update -y', 'yum install -y python3.11 python3.11-pip unzip', 'cd /home/ec2-user', 'aws s3 cp s3://stock-ai-agent-deploy-1770486416/stock-app.zip .', 'unzip -q stock-app.zip', 'python3.11 -m venv venv', 'source venv/bin/activate', 'pip install -r requirements.txt', 'nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > /var/log/streamlit.log 2>&1 &');
        // EC2 Instance
        const instance = new ec2.Instance(this, 'StockAppInstance', {
            vpc,
            instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
            machineImage: ec2.MachineImage.latestAmazonLinux2023(),
            securityGroup: ec2Sg,
            role: ec2Role,
            userData,
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        });
        // Application Load Balancer
        const alb = new elbv2.ApplicationLoadBalancer(this, 'StockAppAlb', {
            vpc,
            internetFacing: true,
            securityGroup: albSg,
        });
        // Target Group
        const targetGroup = new elbv2.ApplicationTargetGroup(this, 'StockAppTargetGroup', {
            vpc,
            port: 8501,
            protocol: elbv2.ApplicationProtocol.HTTP,
            targets: [new targets.InstanceTarget(instance)],
            healthCheck: {
                path: '/',
                interval: cdk.Duration.seconds(30),
                timeout: cdk.Duration.seconds(5),
            },
        });
        // Listener
        alb.addListener('HttpListener', {
            port: 80,
            defaultTargetGroups: [targetGroup],
        });
        // CloudFront Distribution
        const distribution = new cloudfront.Distribution(this, 'StockAppDistribution', {
            defaultBehavior: {
                origin: new origins.LoadBalancerV2Origin(alb, {
                    protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                }),
                viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
                cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
                originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER,
            },
        });
        // Outputs
        new cdk.CfnOutput(this, 'CloudFrontUrl', {
            value: `https://${distribution.distributionDomainName}`,
            description: 'CloudFront URL',
        });
        new cdk.CfnOutput(this, 'AlbDnsName', {
            value: alb.loadBalancerDnsName,
            description: 'ALB DNS Name',
        });
    }
}
exports.StockAppStack = StockAppStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic3RvY2stYXBwLXN0YWNrLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsic3RvY2stYXBwLXN0YWNrLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7OztBQUFBLG1DQUFtQztBQUNuQywyQ0FBMkM7QUFDM0MsZ0VBQWdFO0FBQ2hFLDBFQUEwRTtBQUMxRSx5REFBeUQ7QUFDekQsOERBQThEO0FBQzlELDJDQUEyQztBQUczQyxNQUFhLGFBQWMsU0FBUSxHQUFHLENBQUMsS0FBSztJQUMxQyxZQUFZLEtBQWdCLEVBQUUsRUFBVSxFQUFFLEtBQXNCO1FBQzlELEtBQUssQ0FBQyxLQUFLLEVBQUUsRUFBRSxFQUFFLEtBQUssQ0FBQyxDQUFDO1FBRXhCLE1BQU07UUFDTixNQUFNLEdBQUcsR0FBRyxJQUFJLEdBQUcsQ0FBQyxHQUFHLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRTtZQUMzQyxNQUFNLEVBQUUsQ0FBQztZQUNULFdBQVcsRUFBRSxDQUFDO1NBQ2YsQ0FBQyxDQUFDO1FBRUgseUJBQXlCO1FBQ3pCLE1BQU0sS0FBSyxHQUFHLElBQUksR0FBRyxDQUFDLGFBQWEsQ0FBQyxJQUFJLEVBQUUsa0JBQWtCLEVBQUU7WUFDNUQsR0FBRztZQUNILFdBQVcsRUFBRSx3QkFBd0I7WUFDckMsZ0JBQWdCLEVBQUUsSUFBSTtTQUN2QixDQUFDLENBQUM7UUFDSCxLQUFLLENBQUMsY0FBYyxDQUFDLEdBQUcsQ0FBQyxJQUFJLENBQUMsT0FBTyxFQUFFLEVBQUUsR0FBRyxDQUFDLElBQUksQ0FBQyxHQUFHLENBQUMsRUFBRSxDQUFDLEVBQUUsWUFBWSxDQUFDLENBQUM7UUFFekUseUJBQXlCO1FBQ3pCLE1BQU0sS0FBSyxHQUFHLElBQUksR0FBRyxDQUFDLGFBQWEsQ0FBQyxJQUFJLEVBQUUsa0JBQWtCLEVBQUU7WUFDNUQsR0FBRztZQUNILFdBQVcsRUFBRSx3QkFBd0I7WUFDckMsZ0JBQWdCLEVBQUUsSUFBSTtTQUN2QixDQUFDLENBQUM7UUFDSCxLQUFLLENB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QUFFLHNCQUFzQixFQUFFO1lBQzdFLGVBQWUsRUFBRTtnQkFDZixNQUFNLEVBQUUsSUFBSSxPQUFPLENBQUMsb0JBQW9CLENBQUMsR0FBRyxFQUFFO29CQUM1QyxjQUFjLEVBQUUsVUFBVSxDQUFDLG9CQUFvQixDQUFDLFNBQVM7aUJBQzFELENBQUM7Z0JBQ0Ysb0JBQW9CLEVBQUUsVUFBVSxDQUFDLG9CQUFvQixDQUFDLGlCQUFpQjtnQkFDdkUsY0FBYyxFQUFFLFVBQVUsQ0FBQyxjQUFjLENBQUMsU0FBUztnQkFDbkQsV0FBVyxFQUFFLFVBQVUsQ0FBQyxXQUFXLENBQUMsZ0JBQWdCO2dCQUNwRCxtQkFBbUIsRUFBRSxVQUFVLENBQUMsbUJBQW1CLENBQUMsVUFBVTthQUMvRDtTQUNGLENBQUMsQ0FBQztRQUVILFVBQVU7UUFDVixJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGVBQWUsRUFBRTtZQUN2QyxLQUFLLEVBQUUsV0FBVyxZQUFZLENBQUMsc0JBQXNCLEVBQUU7WUFDdkQsV0FBVyxFQUFFLGdCQUFnQjtTQUM5QixDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLFlBQVksRUFBRTtZQUNwQyxLQUFLLEVBQUUsR0FBRyxDQUFDLG1CQUFtQjtZQUM5QixXQUFXLEVBQUUsY0FBYztTQUM1QixDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUFwSEQsc0NBb0hDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcbmltcG9ydCAqIGFzIGVjMiBmcm9tICdhd3MtY2RrLWxpYi9hd3MtZWMyJztcbmltcG9ydCAqIGFzIGVsYnYyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1lbGFzdGljbG9hZGJhbGFuY2luZ3YyJztcbmltcG9ydCAqIGFzIHRhcmdldHMgZnJvbSAnYXdzLWNkay1saWIvYXdzLWVsYXN0aWNsb2FkYmFsYW5jaW5ndjItdGFyZ2V0cyc7XG5pbXBvcnQgKiBhcyBjbG91ZGZyb250IGZyb20gJ2F3cy1jZGstbGliL2F3cy1jbG91ZGZyb250JztcbmltcG9ydCAqIGFzIG9yaWdpbnMgZnJvbSAnYXdzLWNkay1saWIvYXdzLWNsb3VkZnJvbnQtb3JpZ2lucyc7XG5pbXBvcnQgKiBhcyBpYW0gZnJvbSAnYXdzLWNkay1saWIvYXdzLWlhbSc7XG5pbXBvcnQgeyBDb25zdHJ1Y3QgfSBmcm9tICdjb25zdHJ1Y3RzJztcblxuZXhwb3J0IGNsYXNzIFN0b2NrQXBwU3RhY2sgZXh0ZW5kcyBjZGsuU3RhY2sge1xuICBjb25zdHJ1Y3RvcihzY29wZTogQ29uc3RydWN0LCBpZDogc3RyaW5nLCBwcm9wcz86IGNkay5TdGFja1Byb3BzKSB7XG4gICAgc3VwZXIoc2NvcGUsIGlkLCBwcm9wcyk7XG5cbiAgICAvLyBWUENcbiAgICBjb25zdCB2cGMgPSBuZXcgZWMyLlZwYyh0aGlzLCAnU3RvY2tBcHBWcGMnLCB7XG4gICAgICBtYXhBenM6IDIsXG4gICAgICBuYXRHYXRld2F5czogMSxcbiAgICB9KTtcblxuICAgIC8vIFNlY3VyaXR5IEdyb3VwIGZvciBBTEJcbiAgICBjb25zdCBhbGJTZyA9IG5ldyBlYzIuU2VjdXJpdHlHcm91cCh0aGlzLCAnQWxiU2VjdXJpdHlHcm91cCcsIHtcbiAgICAgIHZwYyxcbiAgICAgIGRlc2NyaXB0aW9uOiAnU2VjdXJpdHkgZ3JvdXAgZm9yIEFMQicsXG4gICAgICBhbGxvd0FsbE91dGJvdW5kOiB0cnVlLFxuICAgIH0pO1xuICAgIGFsYlNnLmFkZEluZ3Jlc3NSdWxlKGVjMi5QZWVyLmFueUlwdjQoKSwgZWMyLlBvcnQudGNwKDgwKSwgJ0FsbG93IEhUVFAnKTtcblxuICAgIC8vIFNlY3VyaXR5IEdyb3VwIGZvciBFQzJcbiAgICBjb25zdCBlYzJTZyA9IG5ldyBlYzIuU2VjdXJpdHlHcm91cCh0aGlzLCAnRWMyU2VjdXJpdHlHcm91cCcsIHtcbiAgICAgIHZwYyxcbiAgICAgIGRlc2NyaXB0aW9uOiAnU2VjdXJpdHkgZ3JvdXAgZm9yIEVDMicsXG4gICAgICBhbGxvd0FsbE91dGJvdW5kOiB0cnVlLFxuICAgIH0pO1xuICAgIGVjMlNnLmFkZEluZ3Jlc3NSdWxlKGFsYlNnLCBlYzIuUG9ydC50Y3AoODUwMSksICdBbGxvdyBTdHJlYW1saXQgZnJvbSBBTEInKTtcblxuICAgIC8vIElBTSBSb2xlIGZvciBFQzJcbiAgICBjb25zdCBlYzJSb2xlID0gbmV3IGlhbS5Sb2xlKHRoaXMsICdFYzJSb2xlJywge1xuICAgICAgYXNzdW1lZEJ5OiBuZXcgaWFtLlNlcnZpY2VQcmluY2lwYWwoJ2VjMi5hbWF6b25hd3MuY29tJyksXG4gICAgICBtYW5hZ2VkUG9saWNpZXM6IFtcbiAgICAgICAgaWFtLk1hbmFnZWRQb2xpY3kuZnJvbUF3c01hbmFnZWRQb2xpY3lOYW1lKCdBbWF6b25TU01NYW5hZ2VkSW5zdGFuY2VDb3JlJyksXG4gICAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnQW1hem9uQmVkcm9ja0Z1bGxBY2Nlc3MnKSxcbiAgICAgIF0sXG4gICAgfSk7XG4gICAgXG4gICAgLy8gUzMgYWNjZXNzIGZvciBkZXBsb3ltZW50XG4gICAgZWMyUm9sZS5hZGRUb1BvbGljeShuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICBhY3Rpb25zOiBbJ3MzOkdldE9iamVjdCddLFxuICAgICAgcmVzb3VyY2VzOiBbJ2Fybjphd3M6czM6OjpzdG9jay1haS1hZ2VudC1kZXBsb3ktMTc3MDQ4NjQxNi8qJ10sXG4gICAgfSkpO1xuXG4gICAgLy8gVXNlciBEYXRhIGZvciBFQzJcbiAgICBjb25zdCB1c2VyRGF0YSA9IGVjMi5Vc2VyRGF0YS5mb3JMaW51eCgpO1xuICAgIHVzZXJEYXRhLmFkZENvbW1hbmRzKFxuICAgICAgJ3l1bSB1cGRhdGUgLXknLFxuICAgICAgJ3l1bSBpbnN0YWxsIC15IHB5dGhvbjMuMTEgcHl0aG9uMy4xMS1waXAgdW56aXAnLFxuICAgICAgJ2NkIC9ob21lL2VjMi11c2VyJyxcbiAgICAgICdhd3MgczMgY3AgczM6Ly9zdG9jay1haS1hZ2VudC1kZXBsb3ktMTc3MDQ4NjQxNi9zdG9jay1hcHAuemlwIC4nLFxuICAgICAgJ3VuemlwIC1xIHN0b2NrLWFwcC56aXAnLFxuICAgICAgJ3B5dGhvbjMuMTEgLW0gdmVudiB2ZW52JyxcbiAgICAgICdzb3VyY2UgdmVudi9iaW4vYWN0aXZhdGUnLFxuICAgICAgJ3BpcCBpbnN0YWxsIC1yIHJlcXVpcmVtZW50cy50eHQnLFxuICAgICAgJ25vaHVwIHN0cmVhbWxpdCBydW4gYXBwLnB5IC0tc2VydmVyLnBvcnQgODUwMSAtLXNlcnZlci5hZGRyZXNzIDAuMC4wLjAgPiAvdmFyL2xvZy9zdHJlYW1saXQubG9nIDI+JjEgJidcbiAgICApO1xuXG4gICAgLy8gRUMyIEluc3RhbmNlXG4gICAgY29uc3QgaW5zdGFuY2UgPSBuZXcgZWMyLkluc3RhbmNlKHRoaXMsICdTdG9ja0FwcEluc3RhbmNlJywge1xuICAgICAgdnBjLFxuICAgICAgaW5zdGFuY2VUeXBlOiBlYzIuSW5zdGFuY2VUeXBlLm9mKGVjMi5JbnN0YW5jZUNsYXNzLlQzLCBlYzIuSW5zdGFuY2VTaXplLk1FRElVTSksXG4gICAgICBtYWNoaW5lSW1hZ2U6IGVjMi5NYWNoaW5lSW1hZ2UubGF0ZXN0QW1hem9uTGludXgyMDIzKCksXG4gICAgICBzZWN1cml0eUdyb3VwOiBlYzJTZyxcbiAgICAgIHJvbGU6IGVjMlJvbGUsXG4gICAgICB1c2VyRGF0YSxcbiAgICAgIHZwY1N1Ym5ldHM6IHsgc3VibmV0VHlwZTogZWMyLlN1Ym5ldFR5cGUuUFJJVkFURV9XSVRIX0VHUkVTUyB9LFxuICAgIH0pO1xuXG4gICAgLy8gQXBwbGljYXRpb24gTG9hZCBCYWxhbmNlclxuICAgIGNvbnN0IGFsYiA9IG5ldyBlbGJ2Mi5BcHBsaWNhdGlvbkxvYWRCYWxhbmNlcih0aGlzLCAnU3RvY2tBcHBBbGInLCB7XG4gICAgICB2cGMsXG4gICAgICBpbnRlcm5ldEZhY2luZzogdHJ1ZSxcbiAgICAgIHNlY3VyaXR5R3JvdXA6IGFsYlNnLFxuICAgIH0pO1xuXG4gICAgLy8gVGFyZ2V0IEdyb3VwXG4gICAgY29uc3QgdGFyZ2V0R3JvdXAgPSBuZXcgZWxidjIuQXBwbGljYXRpb25UYXJnZXRHcm91cCh0aGlzLCAnU3RvY2tBcHBUYXJnZXRHcm91cCcsIHtcbiAgICAgIHZwYyxcbiAgICAgIHBvcnQ6IDg1MDEsXG4gICAgICBwcm90b2NvbDogZWxidjIuQXBwbGljYXRpb25Qcm90b2NvbC5IVFRQLFxuICAgICAgdGFyZ2V0czogW25ldyB0YXJnZXRzLkluc3RhbmNlVGFyZ2V0KGluc3RhbmNlKV0sXG4gICAgICBoZWFsdGhDaGVjazoge1xuICAgICAgICBwYXRoOiAnLycsXG4gICAgICAgIGludGVydmFsOiBjZGsuRHVyYXRpb24uc2Vjb25kcygzMCksXG4gICAgICAgIHRpbWVvdXQ6IGNkay5EdXJhdGlvbi5zZWNvbmRzKDUpLFxuICAgICAgfSxcbiAgICB9KTtcblxuICAgIC8vIExpc3RlbmVyXG4gICAgYWxiLmFkZExpc3RlbmVyKCdIdHRwTGlzdGVuZXInLCB7XG4gICAgICBwb3J0OiA4MCxcbiAgICAgIGRlZmF1bHRUYXJnZXRHcm91cHM6IFt0YXJnZXRHcm91cF0sXG4gICAgfSk7XG5cbiAgICAvLyBDbG91ZEZyb250IERpc3RyaWJ1dGlvblxuICAgIGNvbnN0IGRpc3RyaWJ1dGlvbiA9IG5ldyBjbG91ZGZyb250LkRpc3RyaWJ1dGlvbih0aGlzLCAnU3RvY2tBcHBEaXN0cmlidXRpb24nLCB7XG4gICAgICBkZWZhdWx0QmVoYXZpb3I6IHtcbiAgICAgICAgb3JpZ2luOiBuZXcgb3JpZ2lucy5Mb2FkQmFsYW5jZXJWMk9yaWdpbihhbGIsIHtcbiAgICAgICAgICBwcm90b2NvbFBvbGljeTogY2xvdWRmcm9udC5PcmlnaW5Qcm90b2NvbFBvbGljeS5IVFRQX09OTFksXG4gICAgICAgIH0pLFxuICAgICAgICB2aWV3ZXJQcm90b2NvbFBvbGljeTogY2xvdWRmcm9udC5WaWV3ZXJQcm90b2NvbFBvbGljeS5SRURJUkVDVF9UT19IVFRQUyxcbiAgICAgICAgYWxsb3dlZE1ldGhvZHM6IGNsb3VkZnJvbnQuQWxsb3dlZE1ldGhvZHMuQUxMT1dfQUxMLFxuICAgICAgICBjYWNoZVBvbGljeTogY2xvdWRmcm9udC5DYWNoZVBvbGljeS5DQUNISU5HX0RJU0FCTEVELFxuICAgICAgICBvcmlnaW5SZXF1ZXN0UG9saWN5OiBjbG91ZGZyb250Lk9yaWdpblJlcXVlc3RQb2xpY3kuQUxMX1ZJRVdFUixcbiAgICAgIH0sXG4gICAgfSk7XG5cbiAgICAvLyBPdXRwdXRzXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0Nsb3VkRnJvbnRVcmwnLCB7XG4gICAgICB2YWx1ZTogYGh0dHBzOi8vJHtkaXN0cmlidXRpb24uZGlzdHJpYnV0aW9uRG9tYWluTmFtZX1gLFxuICAgICAgZGVzY3JpcHRpb246ICdDbG91ZEZyb250IFVSTCcsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnQWxiRG5zTmFtZScsIHtcbiAgICAgIHZhbHVlOiBhbGIubG9hZEJhbGFuY2VyRG5zTmFtZSxcbiAgICAgIGRlc2NyaXB0aW9uOiAnQUxCIEROUyBOYW1lJyxcbiAgICB9KTtcbiAgfVxufVxuIl19