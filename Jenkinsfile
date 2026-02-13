pipeline {
    agent any

    environment {
        VENV_DIR      = "venv"
        METRICS_FILE  = "app/artifacts/metrics.json"
        IMAGE_NAME    = "2022bcs0012/lab6"
        BUILD_MODEL   = "false"
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

        stage('Agent + Docker Preflight') {
            steps {
                sh '''
                set -euxo pipefail
                echo "DEBUG: Who am I?"; id || true
                echo "DEBUG: uname:"; uname -a || true
                echo "DEBUG: docker CLI path:"; which docker || true
                echo "DEBUG: docker version:"; docker version || true
                echo "DEBUG: docker info (first 60 lines):"; docker info | head -n 60 || true
                echo "DEBUG: docker.sock perms:"; ls -la /var/run/docker.sock || true
                '''
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
                echo "DEBUG: requirements.txt (first 50 lines):"; head -n 50 requirements.txt || true
                pip install -r requirements.txt
                echo "DEBUG: pip freeze (first 80 lines):"; pip freeze | head -n 80
                '''
            }
        }

        stage('Train Model') {
            steps {
                sh '''
                set -euxo pipefail
                . "$VENV_DIR/bin/activate"
                echo "DEBUG: Running training..."
                ls -la app || true
                ls -la app/artifacts || true
                python -u app/train.py
                echo "DEBUG: After training, artifacts:"; ls -la app/artifacts || true
                '''
            }
        }

        stage('Read Metrics') {
            steps {
                script {
                    echo "DEBUG: Reading metrics from ${METRICS_FILE}"

                    if (!fileExists(METRICS_FILE)) {
                        sh 'echo "DEBUG: find workspace files (maxdepth 4):" && find . -maxdepth 4 -type f -print'
                        error "CRITICAL: Metrics file ${METRICS_FILE} not found!"
                    }

                    def json = readJSON file: "${METRICS_FILE}"
                    echo "DEBUG: Raw JSON map: ${json}"
                    echo "DEBUG: JSON Object Type: ${json.getClass().getName()}"

                    def r2Val = json['r2']
                    def rmseVal = json['rmse']

                    echo "DEBUG: Raw r2 from map: ${r2Val} (Type: ${r2Val?.getClass()?.getName()})"
                    echo "DEBUG: Raw rmse from map: ${rmseVal} (Type: ${rmseVal?.getClass()?.getName()})"

                    if (r2Val == null || rmseVal == null) {
                        error "CRITICAL: metrics.json missing keys. Expected r2 and rmse. Got: ${json}"
                    }

                    env.NEW_R2 = "${r2Val}".trim()
                    env.NEW_RMSE = "${rmseVal}".trim()

                    echo "DEBUG: Parsed New R2 = ${env.NEW_R2}"
                    echo "DEBUG: Parsed New RMSE = ${env.NEW_RMSE}"

                    // Validate parseability
                    try {
                        env.NEW_R2.toFloat()
                        env.NEW_RMSE.toFloat()
                    } catch (Exception e) {
                        error "CRITICAL: Non-numeric metrics. NEW_R2='${env.NEW_R2}', NEW_RMSE='${env.NEW_RMSE}'. Error: ${e}"
                    }
                }
            }
        }

        stage('Compare Metrics') {
            steps {
                withCredentials([
                    string(credentialsId: 'best-r2', variable: 'BASE_R2_FROM_CREDS'),
                    string(credentialsId: 'best-rmse', variable: 'BASE_RMSE_FROM_CREDS')
                ]) {
                    script {
                        echo "DEBUG: Baseline creds raw -> R2='${BASE_R2_FROM_CREDS}', RMSE='${BASE_RMSE_FROM_CREDS}'"

                        env.BASELINE_R2 = (BASE_R2_FROM_CREDS != null && BASE_R2_FROM_CREDS.trim() != "") ? BASE_R2_FROM_CREDS.trim() : "0.0"
                        env.BASELINE_RMSE = (BASE_RMSE_FROM_CREDS != null && BASE_RMSE_FROM_CREDS.trim() != "") ? BASE_RMSE_FROM_CREDS.trim() : "1.0"

                        float nR2 = env.NEW_R2.toFloat()
                        float nRMSE = env.NEW_RMSE.toFloat()
                        float bR2 = env.BASELINE_R2.toFloat()
                        float bRMSE = env.BASELINE_RMSE.toFloat()

                        def r2Improved = nR2 > bR2
                        def rmseImproved = nRMSE < bRMSE

                        echo "DEBUG: Compare -> NEW_R2=${nR2}, BASELINE_R2=${bR2}, r2Improved=${r2Improved}"
                        echo "DEBUG: Compare -> NEW_RMSE=${nRMSE}, BASELINE_RMSE=${bRMSE}, rmseImproved=${rmseImproved}"

                        if (r2Improved || (nR2 == bR2 && rmseImproved)) {
                            env.BUILD_MODEL = "true"
                        } else {
                            env.BUILD_MODEL = "false"
                        }

                        echo "DECISION: BUILD_MODEL=${env.BUILD_MODEL}"
                    }
                }
            }
        }

        stage('Docker Build (Conditional)') {
            when { expression { env.BUILD_MODEL == "true" } }
            steps {
                sh '''
                set -euxo pipefail
                echo "DEBUG: Build context files:"; ls -la
                echo "DEBUG: Dockerfile:"; ls -la Dockerfile || true
                echo "DEBUG: Building image ${IMAGE_NAME}:${BUILD_NUMBER}"
                docker build --progress=plain -t "${IMAGE_NAME}:${BUILD_NUMBER}" .
                echo "DEBUG: Tagging latest"
                docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${IMAGE_NAME}:latest"

                echo "DEBUG: Images (top):"
                docker images | head -n 30

                echo "DEBUG: Inspect built images:"
                docker image inspect "${IMAGE_NAME}:${BUILD_NUMBER}" >/dev/null
                docker image inspect "${IMAGE_NAME}:latest" >/dev/null
                '''
            }
        }

        stage('Docker Push (Conditional)') {
            when { expression { env.BUILD_MODEL == "true" } }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    set -euxo pipefail

                    echo "DEBUG: DockerHub user from creds=$DOCKER_USER"
                    echo "DEBUG: IMAGE_NAME=$IMAGE_NAME"
                    echo "DEBUG: Tags to push: $IMAGE_NAME:$BUILD_NUMBER and $IMAGE_NAME:latest"

                    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                    echo "DEBUG: Pushing $IMAGE_NAME:$BUILD_NUMBER"
                    docker push "$IMAGE_NAME:$BUILD_NUMBER"

                    echo "DEBUG: Pushing $IMAGE_NAME:latest"
                    docker push "$IMAGE_NAME:latest"

                    echo "DEBUG: Logout"
                    docker logout
                    '''
                }
            }
        }

        stage('Verify Push by Pull (Conditional)') {
            when { expression { env.BUILD_MODEL == "true" } }
            steps {
                sh '''
                set -euxo pipefail
                echo "DEBUG: Pulling latest to verify push really exists on registry"
                docker pull "$IMAGE_NAME:latest"
                docker image inspect "$IMAGE_NAME:latest" --format='DEBUG: Pulled OK -> ID={{.Id}} Created={{.Created}}'
                '''
            }
        }
    }

    post {
        always {
            echo "DEBUG: Archiving artifacts under app/artifacts/**"
            sh 'ls -la app/artifacts || true'
            archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
        }
        failure {
            echo "DEBUG: Failure diagnostics"
            sh 'set +e; pwd; ls -la; echo "--- docker images ---"; docker images | head -n 30; echo "--- docker info ---"; docker info | head -n 60'
        }
    }
}
