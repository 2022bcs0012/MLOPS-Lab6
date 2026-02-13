pipeline {
    agent any

    options {
        timestamps()
        ansiColor('xterm')
    }

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
                sh 'set -eux; echo "DEBUG: After checkout"; git rev-parse HEAD || true; git status || true; ls -la'
            }
        }

        // Prove which Jenkinsfile is running
        stage('Print Jenkinsfile (proof)') {
            steps {
                sh '''
                set -euxo pipefail
                echo "=== DEBUG: Jenkinsfile path listing ==="
                ls -la
                echo "=== DEBUG: Jenkinsfile (first 220 lines) ==="
                sed -n '1,220p' Jenkinsfile || true
                '''
            }
        }

        stage('Agent + Tooling Preflight') {
            steps {
                sh '''
                set -euxo pipefail
                echo "=== DEBUG: Agent identity ==="
                id || true
                whoami || true
                uname -a || true
                echo "=== DEBUG: Environment ==="
                env | sort | sed -n '1,120p'
                echo "=== DEBUG: Python ==="
                which python3 || true
                python3 --version || true
                echo "=== DEBUG: Docker ==="
                which docker || true
                docker version || true
                docker info | head -n 80 || true
                ls -la /var/run/docker.sock || true
                '''
            }
        }

        stage('Setup Python Virtual Environment') {
            steps {
                sh '''
                set -euxo pipefail
                rm -rf "$VENV_DIR" || true
                python3 -m venv "$VENV_DIR"
                . "$VENV_DIR/bin/activate"
                python --version
                pip --version
                pip install --upgrade pip
                echo "=== DEBUG: requirements.txt (first 80 lines) ==="
                head -n 80 requirements.txt || true
                pip install -r requirements.txt
                echo "=== DEBUG: pip freeze (first 120 lines) ==="
                pip freeze | sed -n '1,120p'
                '''
            }
        }

        stage('Train Model') {
            steps {
                sh '''
                set -euxo pipefail
                . "$VENV_DIR/bin/activate"

                echo "=== DEBUG: Project tree (key dirs) ==="
                ls -la
                ls -la app || true
                ls -la app/artifacts || true

                echo "=== DEBUG: Running training ==="
                python -u app/train.py

                echo "=== DEBUG: After training artifacts ==="
                ls -la app/artifacts || true

                echo "=== DEBUG: metrics.json content (if exists) ==="
                if [ -f "$METRICS_FILE" ]; then
                  cat "$METRICS_FILE"
                else
                  echo "metrics.json NOT FOUND at $METRICS_FILE"
                fi
                '''
            }
        }

        stage('Read Metrics (Groovy)') {
            steps {
                script {
                    echo "DEBUG: Reading metrics from ${METRICS_FILE}"

                    if (!fileExists(METRICS_FILE)) {
                        sh 'set +e; echo "DEBUG: find workspace files (maxdepth 6):"; find . -maxdepth 6 -type f -print'
                        error "CRITICAL: Metrics file ${METRICS_FILE} not found!"
                    }

                    def json = readJSON file: "${METRICS_FILE}"
                    echo "DEBUG: Raw JSON map: ${json}"
                    echo "DEBUG: JSON type: ${json.getClass().getName()}"

                    def r2Val = json['r2']
                    def rmseVal = json['rmse']

                    echo "DEBUG: Raw r2=${r2Val} (type=${r2Val?.getClass()?.getName()})"
                    echo "DEBUG: Raw rmse=${rmseVal} (type=${rmseVal?.getClass()?.getName()})"

                    if (r2Val == null || rmseVal == null) {
                        error "CRITICAL: metrics.json missing required keys (r2, rmse). Got: ${json}"
                    }

                    env.NEW_R2   = "${r2Val}".trim()
                    env.NEW_RMSE = "${rmseVal}".trim()

                    // Validate numeric and not NaN
                    float nR2_check = env.NEW_R2.toFloat()
                    float nRMSE_check = env.NEW_RMSE.toFloat()
                    if (Float.isNaN(nR2_check) || Float.isNaN(nRMSE_check)) {
                        error "CRITICAL: NEW_R2/NEW_RMSE parsed to NaN. NEW_R2='${env.NEW_R2}', NEW_RMSE='${env.NEW_RMSE}'"
                    }

                    echo "DEBUG: Parsed NEW_R2=${env.NEW_R2}"
                    echo "DEBUG: Parsed NEW_RMSE=${env.NEW_RMSE}"
                }
            }
        }

        stage('Compare Accuracy (Hard Debug)') {
            steps {
                withCredentials([
                    string(credentialsId: 'best-r2', variable: 'BASE_R2_FROM_CREDS'),
                    string(credentialsId: 'best-rmse', variable: 'BASE_RMSE_FROM_CREDS')
                ]) {
                    script {
                        echo "DEBUG: Baseline creds raw -> R2='${BASE_R2_FROM_CREDS}', RMSE='${BASE_RMSE_FROM_CREDS}'"
                        echo "DEBUG: Incoming NEW_R2='${env.NEW_R2}', NEW_RMSE='${env.NEW_RMSE}'"

                        env.BASELINE_R2   = (BASE_R2_FROM_CREDS?.trim())   ? BASE_R2_FROM_CREDS.trim()   : "-999999.0"
                        env.BASELINE_RMSE = (BASE_RMSE_FROM_CREDS?.trim()) ? BASE_RMSE_FROM_CREDS.trim() : "999999.0"

                        float nR2   = env.NEW_R2.toFloat()
                        float nRMSE = env.NEW_RMSE.toFloat()
                        float bR2   = env.BASELINE_R2.toFloat()
                        float bRMSE = env.BASELINE_RMSE.toFloat()

                        if (Float.isNaN(nR2) || Float.isNaN(nRMSE) || Float.isNaN(bR2) || Float.isNaN(bRMSE)) {
                            error "CRITICAL: NaN detected. nR2=${nR2}, nRMSE=${nRMSE}, bR2=${bR2}, bRMSE=${bRMSE}"
                        }

                        boolean r2Improved = (nR2 > bR2)
                        boolean rmseImproved = (nRMSE < bRMSE)

                        echo "DEBUG: nR2=${nR2}, bR2=${bR2}, r2Improved=${r2Improved}"
                        echo "DEBUG: nRMSE=${nRMSE}, bRMSE=${bRMSE}, rmseImproved=${rmseImproved}"

                        env.BUILD_MODEL = (r2Improved || (nR2 == bR2 && rmseImproved)) ? "true" : "false"

                        echo "DECISION (inside Compare): BUILD_MODEL=${env.BUILD_MODEL}"
                        echo "DEBUG: env.BUILD_MODEL class=${env.BUILD_MODEL?.getClass()?.getName()}"
                    }
                }
            }
        }

        stage('Decision Debug (Always)') {
            steps {
                script {
                    echo "DECISION DEBUG (post-compare):"
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

        // Extra proof that the when-condition is evaluated correctly (creates a visible marker file)
        stage('When Condition Probe') {
            steps {
                script {
                    def cond = (env.BUILD_MODEL?.trim() == "true")
                    echo "DEBUG: when-probe cond=${cond} (BUILD_MODEL='${env.BUILD_MODEL}')"
                    sh "set -eux; echo \"cond=${cond}\" > when_probe.txt; cat when_probe.txt"
                    archiveArtifacts artifacts: 'when_probe.txt', fingerprint: true
                }
            }
        }

        stage('Docker Build (Conditional)') {
            when {
                expression {
                    echo "DEBUG(when docker build): BUILD_MODEL='${env.BUILD_MODEL}'"
                    return env.BUILD_MODEL?.trim() == "true"
                }
            }
            steps {
                sh '''
                set -euxo pipefail
                echo "DEBUG: docker version:"
                docker version || true

                echo "DEBUG: Build context listing:"
                ls -la
                ls -la Dockerfile || true

                echo "DEBUG: Building ${IMAGE_NAME}:${BUILD_NUMBER}"
                docker build --progress=plain -t "${IMAGE_NAME}:${BUILD_NUMBER}" .
                docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${IMAGE_NAME}:latest"

                echo "DEBUG: Images:"
                docker images | head -n 40

                docker image inspect "${IMAGE_NAME}:${BUILD_NUMBER}" >/dev/null
                docker image inspect "${IMAGE_NAME}:latest" >/dev/null
                '''
            }
        }

        stage('Docker Push (Conditional)') {
            when {
                expression {
                    echo "DEBUG(when docker push): BUILD_MODEL='${env.BUILD_MODEL}'"
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
                    echo "DEBUG(when verify pull): BUILD_MODEL='${env.BUILD_MODEL}'"
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
            echo "DEBUG: Archiving app/artifacts/**"
            sh 'set +e; ls -la app/artifacts || true'
            archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
        }
        failure {
            echo "DEBUG: Failure diagnostics"
            sh '''
            set +e
            echo "=== pwd/ls ==="; pwd; ls -la
            echo "=== git status ==="; git status || true
            echo "=== docker images ==="; docker images | head -n 40 || true
            echo "=== docker info ==="; docker info | head -n 80 || true
            '''
        }
    }
}
