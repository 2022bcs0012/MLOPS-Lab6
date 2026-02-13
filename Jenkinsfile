pipeline {
  agent any

  options { timestamps() }

  environment {
    VENV_DIR     = "venv"
    METRICS_FILE = "app/artifacts/metrics.json"
  }

  stages {

    stage('Checkout') {
      steps {
        deleteDir()
        dir(env.WORKSPACE) { checkout scm }
        sh 'set -eux; test -d .git; git rev-parse --short HEAD'
      }
    }

    stage('Train') {
      steps {
        sh '''
          set -euxo pipefail
          python3 -m venv "$VENV_DIR"
          . "$VENV_DIR/bin/activate"
          pip install --upgrade pip
          pip install -r requirements.txt
          python -u app/train.py
          test -f "$METRICS_FILE"
          cat "$METRICS_FILE"
        '''
      }
    }

    stage('Build + Push Docker (always)') {
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

            docker version
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin

            docker build -t "$REPO:${BUILD_NUMBER}" .
            docker tag "$REPO:${BUILD_NUMBER}" "$REPO:latest"

            docker push "$REPO:${BUILD_NUMBER}"
            docker push "$REPO:latest"

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
  }
}
