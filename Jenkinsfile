pipeline {
  agent any

  environment {
    REPO_URL = "https://github.com/2022bcs0012/MLOPS-Lab6.git"
    BRANCH   = "main"   // change to master if needed
  }

  stages {
    stage('Clean + Clone (Fix git dir)') {
      steps {
        deleteDir()
        sh '''
          set -euxo pipefail
          echo "DEBUG: before clone"
          pwd
          ls -la
        '''

        // Explicit clone. If repo is private, add: credentialsId: 'github-creds'
        git branch: "${BRANCH}", url: "${REPO_URL}"

        sh '''
          set -euxo pipefail
          echo "DEBUG: after clone"
          ls -la
          test -d .git
          git rev-parse --is-inside-work-tree
          git rev-parse HEAD
          git remote -v
        '''
      }
    }

    stage('Continue') {
      steps {
        echo "Checkout fixed. Continue with your training/build stages here."
      }
    }
  }
}
