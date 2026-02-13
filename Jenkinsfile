pipeline {
  agent any

  options {
    timestamps()
  }

  environment {
    VENV_DIR     = "venv"
    METRICS_FILE = "app/artifacts/metrics.json"
    // repo name is derived from DOCKER_USER at push time
    REPO_NAME    = "lab6"
  }

  stages {

    stage('Checkout') {
      steps {
        sh 'set -eux; pwd; ls -la'
        checkout scm
        sh 'set -eux; git rev-parse HEAD || true; git status || true; ls -la'
      }
    }

    stage('Preflight') {
      steps {
        sh '''
          set -euxo pipefail
          echo "=== whoami/id ==="
          whoami || true
          id || true

          echo "=== python ==="
          which python3 || true
          python3 --version || true

          echo "=== docker (must show Server:) ==="
          which docker || true
          docker version
          docker info | head -n 60

          echo "=== docker.sock check ==="
          ls -la /var/run/docker.sock
        '''
      }
    }

    stage('Setup venv + deps') {
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

    stage('Train') {
      steps {
        sh '''
          set -euxo pipefail
          . "$VENV_DIR/bin/activate"
          python -u app/train.py
          echo "=== artifacts after train ==="
          ls -la app/artifacts || true
          echo "=== metrics file ==="
          test -f "$METRICS_FILE" && cat "$METRICS_FILE" || (echo "MISSING: $METRICS_FILE" && exit 2)
        '''
      }
    }

    stage('Parse metrics') {
      steps {
        sh '''
          set -euxo pipefail
          python3 - << 'PY'
import json, os
p = os.environ["METRICS_FILE"]
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
r2 = d.get("r2"); rmse = d.get("rmse")
print("DEBUG: metrics.json =", d)
if r2 is None or rmse is None:
    raise SystemExit("CRITICAL: metrics.json missing keys r2/rmse")
print("DEBUG: R2 =", float(r2))
print("DEBUG: RMSE =", float(rmse))
PY
        '''
      }
    }

    stage('Build + Push Docker (WORKING)') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'dockerhub-creds',
          usernameVariable: 'DOCKER_USER',
          passwordVariable: 'DOCKER_PASS'
        )]) {
          sh '''
            set -euxo pipefail

            REPO="${DOCKER_USER}/${REPO_NAME}"
            echo "DEBUG: Target repo = $REPO"
            echo "DEBUG: Tags = ${BUILD_NUMBER}, latest"

            echo "DEBUG: Docker login as $DOCKER_USER"
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

            echo "DEBUG: Build"
            docker build --progress=plain -t "$REPO:${BUILD_NUMBER}" .

            echo "DEBUG: Tag latest"
            docker tag "$REPO:${BUILD_NUMBER}" "$REPO:latest"

            echo "DEBUG: Local images proof"
            docker image inspect "$REPO:${BUILD_NUMBER}" >/dev/null
            docker image inspect "$REPO:latest" >/dev/null

            echo "DEBUG: Push (must print digest)"
            docker push "$REPO:${BUILD_NUMBER}"
            docker push "$REPO:latest"

            echo "DEBUG: Proof by pull"
            docker rmi -f "$REPO:latest" || true
            docker pull "$REPO:latest"
            docker image inspect "$REPO:latest" --format='PULLED OK: ID={{.Id}} Created={{.Created}}'

            docker logout
          '''
        }
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
      sh 'set +e; ls -la app/artifacts || true'
    }
  }
}
