pipeline {
    agent any

    environment {
        VENV_DIR     = "venv"
        METRICS_FILE = "app/artifacts/metrics.json"
        IMAGE_NAME   = "2022bcs0012/lab6"
        BUILD_MODEL  = "false"
    }

    stages {

        stage('Checkout') {
            steps {
                echo "DEBUG: Workspace=${env.WORKSPACE}"
                sh 'set -eux; pwd; ls -la'
                checkout scm
                sh 'set -eux; echo "DEBUG: After checkout"; ls -la'
            }
        }

        stage('Setup Python Virtual Environment') {
            steps {
                sh '''
                set -euxo pipefail
                python3 --version
                python3 -m venv "$VENV_DIR"
                . "$VENV_DIR/bin/activate"
                python --version
                pip --version
                pip install --upgrade pip
                pip install -r requirements.txt
                '''
            }
        }

        stage('Train Model') {
            steps {
                sh '''
                set -euxo pipefail
                . "$VENV_DIR/bin/activate"
                echo "DEBUG: Before train, artifacts:"; ls -la app/artifacts || true
                python -u app/train.py
                echo "DEBUG: After train, artifacts:"; ls -la app/artifacts || true
                '''
            }
        }

        stage('Read Metrics') {
            steps {
                script {
                    echo "DEBUG: Reading metrics from ${METRICS_FILE}"

                    if (!fileExists(METRICS_FILE)) {
                        sh 'echo "DEBUG: find (maxdepth 4):" && find . -maxdepth 4 -type f -print'
                        error "CRITICAL: Metrics file ${METRICS_FILE} not found!"
                    }

                    def json = readJSON file: "${METRICS_FILE}"
                    echo "DEBUG: Raw JSON map: ${json}"

                    def r2Val = json['r2']
                    def rmseVal = json['rmse']

                    echo "DEBUG: Raw r2=${r2Val} (type=${r2Val?.getClass()?.getName()})"
                    echo "DEBUG: Raw rmse=${rmseVal} (type=${rmseVal?.getClass()?.getName()})"

                    if (r2Val == null || rmseVal == null) {
                        error "CRITICAL: metrics.json missing required keys (r2, rmse). Got: ${json}"
                    }

                    env.NEW_R2   = "${r2Val}".trim()
                    env.NEW_RMSE = "${rmseVal}".trim()

                    // Validate numeric
                    env.NEW_R2.toFloat()
                    env.NEW_RMSE.toFloat()

                    echo "DEBUG: Parsed NEW_R2=${env.NEW_R2}"
                    echo "DEBUG: Parsed NEW_RMSE=${env.NEW_RMSE}"
                }
            }
        }
        stage('Compare Accuracy') {
        steps {
            withCredentials([
            string(credentialsId: 'best-r2', variable: 'BASE_R2_FROM_CREDS'),
            string(credentialsId: 'best-rmse', variable: 'BASE_RMSE_FROM_CREDS')
            ]) {
            script {
                echo "DEBUG: Baseline creds raw -> R2='${BASE_R2_FROM_CREDS}', RMSE='${BASE_RMSE_FROM_CREDS}'"
                echo "DEBUG: Incoming NEW_R2='${env.NEW_R2}', NEW_RMSE='${env.NEW_RMSE}'"

                // Keep creds if set; otherwise defaults
                env.BASELINE_R2   = (BASE_R2_FROM_CREDS?.trim())   ? BASE_R2_FROM_CREDS.trim()   : "-999999.0"
                env.BASELINE_RMSE = (BASE_RMSE_FROM_CREDS?.trim()) ? BASE_RMSE_FROM_CREDS.trim() : "999999.0"

                float nR2   = env.NEW_R2.toFloat()
                float nRMSE = env.NEW_RMSE.toFloat()
                float bR2   = env.BASELINE_R2.toFloat()
                float bRMSE = env.BASELINE_RMSE.toFloat()

                // Guard against NaN
                if (Float.isNaN(nR2) || Float.isNaN(nRMSE) || Float.isNaN(bR2) || Float.isNaN(bRMSE)) {
                error "CRITICAL: NaN detected. nR2=${nR2}, nRMSE=${nRMSE}, bR2=${bR2}, bRMSE=${bRMSE}"
                }

                boolean r2Improved = (nR2 > bR2)
                boolean rmseImproved = (nRMSE < bRMSE)

                echo "DEBUG: nR2=${nR2}, bR2=${bR2}, r2Improved=${r2Improved}"
                echo "DEBUG: nRMSE=${nRMSE}, bRMSE=${bRMSE}, rmseImproved=${rmseImproved}"

                env.BUILD_MODEL = (r2Improved || (nR2 == bR2 && rmseImproved)) ? "true" : "false"

                echo "DECISION (inside Compare): BUILD_MODEL=${env.BUILD_MODEL}"
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
                docker version || true
                echo "DEBUG: Building ${IMAGE_NAME}:${BUILD_NUMBER}"
                docker build --progress=plain -t "${IMAGE_NAME}:${BUILD_NUMBER}" .
                docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${IMAGE_NAME}:latest"
                docker images | head -n 30
                docker image inspect "${IMAGE_NAME}:${BUILD_NUMBER}" >/dev/null
                docker image inspect "${IMAGE_NAME}:latest" >/dev/null
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
                    echo "DEBUG: DOCKER_USER=$DOCKER_USER"
                    echo "DEBUG: Pushing ${IMAGE_NAME}:${BUILD_NUMBER} and ${IMAGE_NAME}:latest"
                    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                    docker push "${IMAGE_NAME}:${BUILD_NUMBER}"
                    docker push "${IMAGE_NAME}:latest"
                    docker logout
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
                docker pull "${IMAGE_NAME}:latest"
                docker image inspect "${IMAGE_NAME}:latest" --format='DEBUG: Pulled OK -> ID={{.Id}}'
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
        }
        failure {
            echo "DEBUG: Failure diagnostics"
            sh 'set +e; pwd; ls -la; docker images | head -n 30 || true; docker info | head -n 60 || true'
        }
    }
}
