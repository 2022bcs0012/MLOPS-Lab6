pipeline {
    agent any

    environment {
        VENV_DIR = "venv"
        METRICS_FILE = "app/artifacts/metrics.json"
        IMAGE_NAME = "2022bcs0012/lab6"

        NEW_R2 = ""
        NEW_RMSE = ""
        BASELINE_R2 = ""
        BASELINE_RMSE = ""
        BUILD_MODEL = "false"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python Virtual Environment') {
            steps {
                sh '''
                python3 -m venv $VENV_DIR
                . $VENV_DIR/bin/activate
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Train Model') {
            steps {
                sh '''
                . $VENV_DIR/bin/activate
                python app/train.py
                '''
            }
        }

        stage('Read Accuracy') {
            steps {
                script {
                    def json = readJSON file: "${METRICS_FILE}"

                    env.NEW_R2 = json.r2.toString()
                    env.NEW_RMSE = json.rmse.toString()

                    echo "New R2 = ${env.NEW_R2}"
                    echo "New RMSE = ${env.NEW_RMSE}"
                }
            }
        }

        stage('Compare Accuracy') {
            steps {
                withCredentials([
                    string(credentialsId: 'best-r2', variable: 'BASE_R2'),
                    string(credentialsId: 'best-rmse', variable: 'BASE_RMSE')
                ]) {
                    script {

                        env.BASELINE_R2 = BASE_R2
                        env.BASELINE_RMSE = BASE_RMSE

                        def r2Improved =
                            env.NEW_R2.toFloat() > env.BASELINE_R2.toFloat()

                        def rmseImproved =
                            env.NEW_RMSE.toFloat() < env.BASELINE_RMSE.toFloat()

                        echo "Baseline R2 = ${env.BASELINE_R2}"
                        echo "Baseline RMSE = ${env.BASELINE_RMSE}"
                        echo "R2 Improved = ${r2Improved}"
                        echo "RMSE Improved = ${rmseImproved}"

                        if (r2Improved ||
                           (env.NEW_R2 == env.BASELINE_R2 && rmseImproved)) {

                            env.BUILD_MODEL = "true"
                            echo "Model accepted for deployment."
                        } else {
                            env.BUILD_MODEL = "false"
                            echo "Model rejected."
                        }
                    }
                }
            }
        }

        stage('Build Docker Image (Conditional)') {
            when {
                expression { env.BUILD_MODEL == "true" }
            }
            steps {
                sh """
                docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest
                """
            }
        }

        stage('Push Docker Image (Conditional)') {
            when {
                expression { env.BUILD_MODEL == "true" }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                    docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                    docker push ${IMAGE_NAME}:latest
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
        }
    }
}
