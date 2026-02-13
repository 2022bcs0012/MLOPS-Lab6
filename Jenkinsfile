pipeline {
    agent any

    options { timestamps() }

    environment {
        VENV_DIR     = "venv"
        METRICS_FILE = "app/artifacts/metrics.json"
        IMAGE_NAME   = "2022bcs0012/lab6"
        BUILD_MODEL  = "false"
    }

    stages {

        stage('Checkout') {
            steps {
                deleteDir()
                dir(env.WORKSPACE) { checkout scm }
                sh 'set -eux; pwd; ls -la; test -d .git; git rev-parse HEAD'
            }
        }

        stage('Agent + Tooling Preflight') {
            steps {
                sh '''
                set -euxo pipefail
                id
                whoami
                uname -a
                which python3
                python3 --version
                which docker
                docker version
                docker info | head -n 60
                ls -la /var/run/docker.sock
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
                python -u app/train.py
                ls -la app/artifacts || true
                '''
            }
        }

        stage('Read Metrics (Python -> env, no plugins)') {
            steps {
                script {
                    def out = sh(
                        script: '''
                          set -euo pipefail
                          test -f "$METRICS_FILE" || (echo "CRITICAL: Missing $METRICS_FILE" >&2 && exit 2)

                          python3 - << 'PY'
import json, os, math
p = os.environ["METRICS_FILE"]
d = json.load(open(p, "r", encoding="utf-8"))
r2 = float(d["r2"])
rmse = float(d["rmse"])
if math.isnan(r2) or math.isnan(rmse):
    raise SystemExit("NaN in metrics")
print(f"{r2} {rmse}")
PY
                        ''',
                        returnStdout: true
                    ).trim()

                    def parts = out.split("\\s+")
                    if (parts.size() != 2) {
                        error "CRITICAL: Unexpected metrics parse output: '${out}'"
                    }

                    env.NEW_R2 = parts[0]
                    env.NEW_RMSE = parts[1]
                    env.NEW_R2.toFloat()
                    env.NEW_RMSE.toFloat()

                    echo "DEBUG: NEW_R2=${env.NEW_R2}, NEW_RMSE=${env.NEW_RMSE}"
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
                        env.BASELINE_R2   = (BASE_R2_FROM_CREDS?.trim())   ? BASE_R2_FROM_CREDS.trim()   : "-999999.0"
                        env.BASELINE_RMSE = (BASE_RMSE_FROM_CREDS?.trim()) ? BASE_RMSE_FROM_CREDS.trim() : "999999.0"

                        float nR2   = env.NEW_R2.toFloat()
                        float nRMSE = env.NEW_RMSE.toFloat()
                        float bR2   = env.BASELINE_R2.toFloat()
                        float bRMSE = env.BASELINE_RMSE.toFloat()

                        boolean r2Improved = (nR2 > bR2)
                        boolean rmseImproved = (nRMSE < bRMSE)

                        env.BUILD_MODEL = (r2Improved || (nR2 == bR2 && rmseImproved)) ? "true" : "false"
                        echo "DECISION: BUILD_MODEL=${env.BUILD_MODEL} (nR2=${nR2}, bR2=${bR2}, nRMSE=${nRMSE}, bRMSE=${bRMSE})"
                    }
                }
            }
        }

        stage('Docker Build (Conditional)') {
            when { expression { env.BUILD_MODEL?.trim() == "true" } }
            steps {
                sh '''
                set -euxo pipefail
                docker version
                docker build --progress=plain -t "${IMAGE_NAME}:${BUILD_NUMBER}" .
                docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${IMAGE_NAME}:latest"
                docker image inspect "${IMAGE_NAME}:latest" >/dev/null
                '''
            }
        }

        stage('Docker Push (Conditional, safe namespace)') {
            when { expression { env.BUILD_MODEL?.trim() == "true" } }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    set -euxo pipefail
                    REPO="${DOCKER_USER}/lab6"

                    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                    docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "$REPO:${BUILD_NUMBER}"
                    docker tag "${IMAGE_NAME}:latest" "$REPO:latest"

                    docker push "$REPO:${BUILD_NUMBER}"
                    docker push "$REPO:latest"

                    docker logout
                    '''
                }
            }
        }

        stage('Verify Push by Pull (Conditional)') {
            when { expression { env.BUILD_MODEL?.trim() == "true" } }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    set -euxo pipefail
                    REPO="${DOCKER_USER}/lab6"
                    docker pull "$REPO:latest"
                    docker image inspect "$REPO:latest" --format='PULLED OK: ID={{.Id}} Created={{.Created}}'
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
        }
        failure {
            sh '''
            set +e
            pwd; ls -la
            git status || true
            docker info | head -n 80 || true
            docker images | head -n 40 || true
            '''
        }
    }
}
