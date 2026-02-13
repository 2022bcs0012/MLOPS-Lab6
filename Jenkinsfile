pipeline {
    agent any

    environment {
        VENV_DIR = "venv"
        METRICS_FILE = "app/artifacts/metrics.json"
        IMAGE_NAME = "2022bcs0012/lab6"
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
                    echo "DEBUG: JSON Object Type: ${json.getClass().getName()}"

                    // Use bracket notation for more robust access
                    def r2Val = json['r2']
                    def rmseVal = json['rmse']
                    
                    echo "DEBUG: Raw r2 from map: ${r2Val} (Type: ${r2Val?.getClass()?.getName()})"
                    echo "DEBUG: Raw rmse from map: ${rmseVal} (Type: ${rmseVal?.getClass()?.getName()})"

                    env.NEW_R2 = "${r2Val}"
                    env.NEW_RMSE = "${rmseVal}"

                    echo "DEBUG: Parsed New R2 = ${env.NEW_R2}"
                    echo "DEBUG: Parsed New RMSE = ${env.NEW_RMSE}"
                }
            }
        }

        stage('Compare Accuracy') {
            steps {
                script {
                    echo "DEBUG: Entering Compare Accuracy stage"
                    echo "DECISION: BUILD_MODEL=${env.BUILD_MODEL} (nR2=${nR2}, bR2=${bR2}, nRMSE=${nRMSE}, bRMSE=${bRMSE})"

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
        stage('Decision Debug (Always)') {
            steps {
                script {
                    echo "DECISION DEBUG:"
                    echo "  BUILD_MODEL=${env.BUILD_MODEL}"
                    echo "  NEW_R2=${env.NEW_R2}"
                    echo "  NEW_RMSE=${env.NEW_RMSE}"
                    echo "  BASELINE_R2=${env.BASELINE_R2}"
                    echo "  BASELINE_RMSE=${env.BASELINE_RMSE}"
                    echo "  IMAGE_NAME=${env.IMAGE_NAME}"
                    echo "  BUILD_NUMBER=${env.BUILD_NUMBER}"
                }
            }
        }

        stage('Docker Build (Conditional)') {
            when {
                expression {
                    echo "DEBUG(when): BUILD_MODEL=${env.BUILD_MODEL}"
                    return env.BUILD_MODEL?.trim() == "true"
                }
            }
            steps {
                sh '''
                set -euxo pipefail
                docker build --progress=plain -t "${IMAGE_NAME}:${BUILD_NUMBER}" .
                docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${IMAGE_NAME}:latest"
                '''
            }
        }

        stage('Docker Push (Conditional)') {
            when {
                expression {
                    echo "DEBUG(when): BUILD_MODEL=${env.BUILD_MODEL}"
                    return env.BUILD_MODEL?.trim() == "true"
                }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    set -euxo pipefail
                    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                    docker push "$IMAGE_NAME:$BUILD_NUMBER"
                    docker push "$IMAGE_NAME:latest"
                    '''
                }
            }
        }

        stage('Verify Push by Pull (Conditional)') {
            when {
                expression {
                    echo "DEBUG(when): BUILD_MODEL=${env.BUILD_MODEL}"
                    return env.BUILD_MODEL?.trim() == "true"
                }
            }
            steps {
                sh '''
                set -euxo pipefail
                docker pull "$IMAGE_NAME:latest"
                '''
            }
        }

    }

    post {
        always {
            archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
        }
    }
}
