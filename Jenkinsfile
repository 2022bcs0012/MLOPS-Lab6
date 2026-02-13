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
                sh """
                . ${VENV_DIR}/bin/activate
                python app/train.py
                """
            }
        }

        stage('Read Accuracy') {
            steps {
                script {
                    echo "DEBUG: Reading metrics from ${METRICS_FILE}"
                    if (!fileExists(METRICS_FILE)) {
                        error "CRITICAL: Metrics file ${METRICS_FILE} not found!"
                    }
                    def json = readJSON file: "${METRICS_FILE}"
                    echo "DEBUG: Raw JSON content: ${json}"

                    env.NEW_R2 = (json.r2 != null) ? json.r2.toString() : "0.0"
                    env.NEW_RMSE = (json.rmse != null) ? json.rmse.toString() : "1.0"

                    echo "DEBUG: Parsed New R2 = ${env.NEW_R2}"
                    echo "DEBUG: Parsed New RMSE = ${env.NEW_RMSE}"
                }
            }
        }

        stage('Compare Accuracy') {
            steps {
                script {
                    echo "DEBUG: Entering Compare Accuracy stage"
                }
                withCredentials([
                    string(credentialsId: 'best-r2', variable: 'BASE_R2_FROM_CREDS'),
                    string(credentialsId: 'best-rmse', variable: 'BASE_RMSE_FROM_CREDS')
                ]) {
                    script {
                        echo "DEBUG: Baseline credentials retrieved"
                        
                        // Handle null/empty credentials gracefully
                        env.BASELINE_R2 = (BASE_R2_FROM_CREDS != null && BASE_R2_FROM_CREDS != "") ? BASE_R2_FROM_CREDS : "0.0"
                        env.BASELINE_RMSE = (BASE_RMSE_FROM_CREDS != null && BASE_RMSE_FROM_CREDS != "") ? BASE_RMSE_FROM_CREDS : "1.0"

                        echo "DEBUG: Comparison Values -> New R2: ${env.NEW_R2}, Baseline R2: ${env.BASELINE_R2}"
                        echo "DEBUG: Comparison Values -> New RMSE: ${env.NEW_RMSE}, Baseline RMSE: ${env.BASELINE_RMSE}"

                        float nR2 = env.NEW_R2.toFloat()
                        float nRMSE = env.NEW_RMSE.toFloat()
                        float bR2 = env.BASELINE_R2.toFloat()
                        float bRMSE = env.BASELINE_RMSE.toFloat()

                        def r2Improved = nR2 > bR2
                        def rmseImproved = nRMSE < bRMSE

                        echo "DEBUG: R2 Improvement check: ${nR2} > ${bR2} -> ${r2Improved}"
                        echo "DEBUG: RMSE Improvement check: ${nRMSE} < ${bRMSE} -> ${rmseImproved}"

                        if (r2Improved || (nR2 == bR2 && rmseImproved)) {
                            env.BUILD_MODEL = "true"
                            echo "SUCCESS: Model performance improved. Triggering build/push."
                        } else {
                            env.BUILD_MODEL = "false"
                            echo "INFO: Model performance did not improve. skipping build."
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
                    sh """
                    echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                    docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                    docker push ${IMAGE_NAME}:latest
                    """
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
