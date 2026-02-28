pipeline {
  agent any

  options { timestamps() }

  environment {
    IMAGE_NAME     = "2022bcs0012/lab7:latest"
    CONTAINER_NAME = "ml_inference_test"
    HOST_PORT      = "8000"
    CONTAINER_PORT = "8000"
    HEALTH_URL     = "http://localhost:8000/health"
    PREDICT_URL    = "http://localhost:8000/predict"
  }

  stages {

    stage('Checkout') {
      steps {
        deleteDir()
        checkout scm
      }
    }

    stage('Pull Docker Image') {
      steps {
        sh '''
          set -euxo pipefail
          docker pull $IMAGE_NAME
        '''
      }
    }

    stage('Run Container') {
      steps {
        sh '''
          set -euxo pipefail
          docker rm -f $CONTAINER_NAME || true
          docker run -d -p $HOST_PORT:$CONTAINER_PORT \
            --name $CONTAINER_NAME $IMAGE_NAME
          docker ps
        '''
      }
    }

    stage('Wait for Service Readiness') {
      steps {
        script {
          def retries = 10
          def ready = false

          for (int i = 0; i < retries; i++) {
            def status = sh(
              script: "curl -s -o /dev/null -w '%{http_code}' $HEALTH_URL || true",
              returnStdout: true
            ).trim()

            echo "Health check status: ${status}"

            if (status == "200") {
              ready = true
              break
            }

            sleep 5
          }

          if (!ready) {
            error "Service did not start within timeout."
          }
        }
      }
    }

    stage('Valid Inference Test') {
      steps {
        script {
          def response = sh(
            script: """
              curl -s -X POST $PREDICT_URL \
              -H "Content-Type: application/json" \
              -d @valid.json
            """,
            returnStdout: true
          ).trim()

          echo "Valid Response: ${response}"

          if (!response.contains("prediction")) {
            error "Prediction field missing."
          }

          def numericCheck = sh(
            script: """
              echo '${response}' | grep -E '"prediction":[ ]*[0-9.]+' || true
            """,
            returnStdout: true
          ).trim()

          if (numericCheck == "") {
            error "Prediction is not numeric."
          }

          echo "Valid inference test passed."
        }
      }
    }

    stage('Invalid Inference Test') {
      steps {
        script {
          def status = sh(
            script: """
              curl -s -o invalid_response.txt -w '%{http_code}' \
              -X POST $PREDICT_URL \
              -H "Content-Type: application/json" \
              -d @invalid.json
            """,
            returnStdout: true
          ).trim()

          def body = sh(
            script: "cat invalid_response.txt",
            returnStdout: true
          ).trim()

          echo "Invalid status: ${status}"
          echo "Invalid body: ${body}"

          if (status == "200") {
            error "Invalid request should not return 200."
          }

          if (!body.toLowerCase().contains("detail")) {
            error "Meaningful error message missing."
          }

          echo "Invalid inference test passed."
        }
      }
    }
  }

  post {
    always {
      sh '''
        docker rm -f $CONTAINER_NAME || true
      '''
    }

    success {
      echo "PIPELINE PASSED: Inference validation successful."
    }

    failure {
      echo "PIPELINE FAILED: Validation error detected."
    }
  }
}