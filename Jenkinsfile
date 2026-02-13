pipeline {
  agent any

  environment {
    VENV_DIR     = "venv"
    METRICS_FILE = "app/artifacts/metrics.json"

    // Git
    REPO_URL = "https://github.com/2022bcs0012/MLOPS-Lab6.git"
    BRANCH   = "main" // change to master if needed

    // Docker repo name (namespace derived from DockerHub login)
    REPO_NAME = "lab6"
  }

  stages {

    stage('Clean + Checkout') {
      steps {
        deleteDir()

        // If repo is private, add: credentialsId: 'github-creds'
        git branch: "${BRANCH}", url: "${REPO_URL}"

        sh '''
          set -euxo pipefail
          echo "=== DEBUG: git ok ==="
          test -d .git
          git rev-parse --is-inside-work-tree
          git rev-parse HEAD
          ls -la
        '''
      }
    }

    stage('Docker Preflight') {
      steps {
        sh '''
          set -euxo pipefail
          docker version
          ls -la /var/run/docker.sock
        '''
      }
    }

    stage('Setup Python venv') {
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

    stage('Train') {
      steps {
        sh '''
          set -euxo pipefail
          . "$VENV_DIR/bin/activate"
          python -u app/train.py
          test -f "$METRICS_FILE" && cat "$METRICS_FILE"
        '''
      }
    }

    stage('Build + Push Docker') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'dockerhub-creds',
          usernameVariable: 'DOCKER_USER',
          passwordVariable: 'DOCKER_PASS'
        )]) {
          sh '''
            set -euxo pipefail
            REPO="${DOCKER_USER}/${REPO_NAME}"
            echo "DEBUG: pushing to $REPO"

            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

            docker build --progress=plain -t "$REPO:${BUILD_NUMBER}" .
            docker tag "$REPO:${BUILD_NUMBER}" "$REPO:latest"

            docker push "$REPO:${BUILD_NUMBER}"
            docker push "$REPO:latest"

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
  }
}
