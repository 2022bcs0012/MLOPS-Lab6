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

    stage('Docker Push Debug (FORCE)') {
    steps {
        withCredentials([usernamePassword(
        credentialsId: 'dockerhub-creds',
        usernameVariable: 'DOCKER_USER',
        passwordVariable: 'DOCKER_PASS'
        )]) {
        sh '''
        set -euxo pipefail

        echo "=== DEBUG: Docker availability ==="
        which docker
        docker version
        docker info | head -n 80

        echo "=== DEBUG: DockerHub login ==="
        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

        # IMPORTANT: always push to the authenticated user's namespace
        REPO="${DOCKER_USER}/lab6"
        echo "=== DEBUG: Target repo ==="
        echo "REPO=$REPO"

        echo "=== DEBUG: Build image ==="
        docker build --progress=plain -t "$REPO:${BUILD_NUMBER}" .

        echo "=== DEBUG: Tag latest ==="
        docker tag "$REPO:${BUILD_NUMBER}" "$REPO:latest"

        echo "=== DEBUG: Confirm local images exist ==="
        docker images | head -n 50
        docker image inspect "$REPO:${BUILD_NUMBER}" >/dev/null
        docker image inspect "$REPO:latest" >/dev/null

        echo "=== DEBUG: Push (this must print layer upload + digest) ==="
        docker push "$REPO:${BUILD_NUMBER}"
        docker push "$REPO:latest"

        echo "=== DEBUG: PROOF (pull back from registry) ==="
        docker rmi -f "$REPO:latest" || true
        docker pull "$REPO:latest"
        docker image inspect "$REPO:latest" --format='PULLED OK: ID={{.Id}} Created={{.Created}}'

        echo "=== DEBUG: Logout ==="
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
