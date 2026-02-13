pipeline {
  agent any

  environment {
    VENV_DIR     = "venv"
    METRICS_FILE = "app/artifacts/metrics.json"

    // Git repo settings
    REPO_URL = "https://github.com/2022bcs0012/MLOPS-Lab6.git"
    BRANCH   = "main"   // change to "master" if your repo uses master
  }

  stages {

    stage('Checkout (Hard)') {
      steps {
        deleteDir()
        git branch: "${BRANCH}", url: "${REPO_URL}"

        sh '''
          set -euxo pipefail
          echo "=== DEBUG: In workspace ==="
          pwd
          ls -la
          test -d .git
          git rev-parse --is-inside-work-tree
          git rev-parse HEAD
          git remote -v
        '''
      }
    }

    stage('Preflight') {
      steps {
        sh '''
          set -euxo pipefail
          echo "=== docker must show Server: ==="
          docker version
          echo "=== docker sock must exist ==="
          ls -la /var/run/docker.sock
          echo "=== python ==="
          python3 --version
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
          echo "=== artifacts ==="
          ls -la app/artifacts || true
          test -f "$METRICS_FILE" && cat "$METRICS_FILE" || (echo "MISSING: $METRICS_FILE" && exit 2)
        '''
      }
    }

    stage('Parse Metrics (No readJSON plugin)') {
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

    // For lab reliability: always build+push (remove condition).
    stage('Build + Push Docker (WORKING)') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'dockerhub-creds',
          usernameVariable: 'DOCKER_USER',
          passwordVariable: 'DOCKER_PASS'
        )]) {
          sh '''
            set -euxo pipefail

            REPO="${DOCKER_USER}/lab6"
            echo "DEBUG: Target repo=$REPO"

            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

            docker build --progress=plain -t "$REPO:${BUILD_NUMBER}" .
            docker tag "$REPO:${BUILD_NUMBER}" "$REPO:latest"

            docker push "$REPO:${BUILD_NUMBER}"
            docker push "$REPO:latest"

            # proof
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
    }
    failure {
      sh '''
        set +e
        echo "=== failure diagnostics ==="
        pwd
        ls -la
        docker info | head -n 80 || true
        docker images | head -n 40 || true
      '''
    }
  }
}
