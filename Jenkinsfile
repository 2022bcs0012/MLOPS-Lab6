pipeline {
    agent any

    options {
        timestamps()
    }

    environment {
        VENV_DIR     = "venv"
        METRICS_FILE = "app/artifacts/metrics.json"
        IMAGE_NAME   = "2022bcs0012/lab6"   // keep, but push will use DOCKER_USER namespace safely
        BUILD_MODEL  = "false"
    }

    stages {

        stage('Checkout') {
            steps {
                // Avoid @tmp git issues after container/workspace changes
                deleteDir()
                dir(env.WORKSPACE) {
                    checkout scm
                }
                sh 'set -eux; pwd; ls -la; test -d .git; git rev-parse HEAD'
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

                echo "=== DEBUG: Python ==="
                which python3 || true
                python3 --version || true

                echo "=== DEBUG: Docker (must show Server:) ==="
                which docker || true
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
                python -u app/train.py
                echo "=== DEBUG: artifacts ==="
                ls -la app/artifacts || true
                '''
            }
        }

        stage('Read Metrics (Python, no Jenkins plugins)') {
            steps {
                sh '''
                set -euxo pipefail
                test -f "$METRICS_FILE" || (echo "CRITICAL: Missing $METRICS_FILE" && find . -maxdepth 6 -type f -print && exit 2)

                python3 - << 'PY'
import json, os, math
p = os.environ["METRICS_FILE"]
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)

r2 = d.get("r2", None)
rmse = d.get("rmse", None)
print("DEBUG: metrics.json =", d)

if r2 is None or rmse is None:
    raise SystemExit("CRITICAL: metrics.json missing keys r2/rmse")

r2 = float(r2)
rmse = float(rmse)

if math.isnan(r2) or math.isnan(rmse):
    raise SystemExit(f"CRITICAL: NaN in metrics: r2={r2}, rmse={rmse}")

# Write to env file for Jenkins to load
with open("metrics.env", "w", encoding="utf-8") as out:
    out.write(f"NEW_R2={r2}\\n")
    out.write(f"NEW_RMSE={rmse}\\n")

print(f"DEBUG: NEW_R2={r2}")
print(f"DEBUG: NEW_RMSE={rmse}")
PY

                echo "=== DEBUG: metrics.env ==="
                cat metrics.env
                '''
                script {
                    def props = readProperties file: 'metrics.env'
                    env.NEW_R2 = props['NEW_R2']?.trim()
                    env.NEW_RMSE = props['NEW_RMSE']?.trim()
                    echo "DEBUG(Groovy): NEW_R2=${env.NEW_R2}, NEW_RMSE=${env.NEW_RMSE}"
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

        stage('Decision Debug') {
            steps {
                script {
                    echo "DECISION DEBUG:"
                    echo "  BUILD_MODEL=${env.BUILD_MODEL}"
                    echo "  NEW_R2=${env.NEW_R2}"
                    echo "  NEW_RMSE=${env.NEW_RMSE}"
                    echo "  BASELINE_R2=${env.BASELINE_R2}"
                    echo "  BASELINE_RMSE=${env.BASELINE_RMSE}"
                    echo "  BUILD_NUMBER=${env.BUILD_NUMBER}"
                }
            }
        }

        stage('Docker Build (Conditional)') {
            when { expression { env.BUILD_MODEL?.trim() == "true" } }
            steps {
                sh '''
                set -euxo pipefail
                docker version

                echo "DEBUG: Building ${IMAGE_NAME}:${BUILD_NUMBER}"
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

                    # Push to the authenticated DockerHub namespace to avoid permission issues
                    REPO="${DOCKER_USER}/lab6"

                    echo "DEBUG: Logging in as $DOCKER_USER"
                    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

                    echo "DEBUG: Tagging local image to $REPO"
                    docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "$REPO:${BUILD_NUMBER}"
                    docker tag "${IMAGE_NAME}:latest" "$REPO:latest"

                    echo "DEBUG: Pushing $REPO:${BUILD_NUMBER} and $REPO:latest"
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
            archiveArtifacts artifacts: 'app/artifacts/**,metrics.env', fingerprint: true
        }
        failure {
            sh '''
            set +e
            echo "=== failure diagnostics ==="
            pwd; ls -la
            git status || true
            docker info | head -n 80 || true
            docker images | head -n 40 || true
            '''
        }
    }
}
