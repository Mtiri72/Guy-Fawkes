pipeline {
    agent any

    environment {
        REGISTRY = "your_dockerhub_username/your_repository"
        REGISTRY_CREDENTIALS = 'docker-registry-credentials'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        KUBECONFIG_CREDENTIALS = 'kubeconfig'
    }

    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/your_username/your_repository.git'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    dockerImage = docker.build("${REGISTRY}:${IMAGE_TAG}")
                }
            }
        }
        stage('Test') {
            steps {
                // Add your test commands here
                // Example: python -m unittest discover tests
                sh 'echo "No tests specified"'
            }
        }
        stage('Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('', REGISTRY_CREDENTIALS) {
                        dockerImage.push()
                    }
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([file(credentialsId: KUBECONFIG_CREDENTIALS, variable: 'KUBECONFIG_FILE')]) {
                    sh """
                        export KUBECONFIG=$KUBECONFIG_FILE
                        kubectl set image deployment/your_deployment your_container=${REGISTRY}:${IMAGE_TAG} --record
                    """
                }
            }
        }
    }
    post {
        always {
            cleanWs()
        }
    }
}
