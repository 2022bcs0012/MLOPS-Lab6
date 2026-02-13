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
        echo "DEBUG: workspace=${env.WORKSPACE}"
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

          echo "=== docker ==="
          which docker || true
          docker version || true
          docker info | head -n 40 || true

          echo "=== key paths ==="
          ls -la app || true
          ls -la app/artifacts || true
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

    stage('Parse metrics (no Jenkins plugins)') {
      steps {
        sh '''
          set -euxo pipefail
          . "$VENV_DIR/bin/activate"

          # Parse JSON with python to avoid readJSON plugin dependency
          python - << 'PY'
import json, os
p = os.environ["METRICS_FILE"]
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)
r2 = d.get("r2", None)
rmse = d.get("rmse", None)
print("DEBUG: metrics.json =", d)
if r2 is None or rmse is None:
    raise SystemExit("CRITICAL: metrics.json missing keys r2/rmse")
print(f"R2={float(r2)}")
print(f"RMSE={float(rmse)}")
PY
        '''
      }
    }

    // Force docker stages to run for debugging (remove later)
    stage('Force Docker = ON (debug)') {
      steps {
        script {
          env.BUILD_MODEL = "true"
          echo "DEBUG: Forcing BUILD_MODEL=true for this run"
        }
      }
    }

    stage('Docker Build') {
      when { expression { env.BUILD_MODEL == "true" } }
      steps {
        sh '''
          set -euxo pipefail
          docker build --progress=plain -t "${IMAGE_NAME}:${BUILD_NUMBER}" .
          docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${IMAGE_NAME}:latest"
          docker images | head -n 30
        '''
      }
    }

    stage('Docker Push') {
      when { expression { env.BUILD_MODEL == "true" } }
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'dockerhub-creds',
          usernameVariable: 'DOCKER_USER',
          passwordVariable: 'DOCKER_PASS'
        )]) {
          sh '''
            set -euxo pipefail
            echo "DEBUG: DOCKER_USER=$DOCKER_USER"
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
            docker push "${IMAGE_NAME}:${BUILD_NUMBER}"
            docker push "${IMAGE_NAME}:latest"
            docker logout
          '''
        }
      }
    }
  }

  post {
    always {
      sh 'set +e; ls -la app/artifacts || true'
      archiveArtifacts artifacts: 'app/artifacts/**', fingerprint: true
    }
  }
}
