pipeline {
  agent any

  environment {
    REPO_URL = "https://github.com/2022bcs0012/MLOPS-Lab6.git"
    BRANCH   = "main"
  }

  options {
    skipDefaultCheckout(true)   // important: prevents Jenkins doing an implicit checkout elsewhere
  }

  stages {

    stage('Clean + Clone (Fix git dir)') {
      steps {
        deleteDir()

        sh '''
          set -euxo pipefail
          echo "DEBUG: WORKSPACE=$WORKSPACE"
          pwd
          ls -la
        '''

        // Explicit clone into current workspace
        dir(env.WORKSPACE) {
          git branch: env.BRANCH, url: env.REPO_URL
        }

        sh '''
          set -euxo pipefail
          echo "DEBUG: after clone"
          echo "DEBUG: WORKSPACE=$WORKSPACE"
          pwd
          ls -la
          test -d .git
          git rev-parse --is-inside-work-tree
          git rev-parse HEAD
          git remote -v
        '''
      }
    }

    stage('Prove every later stage is in the same git repo') {
      steps {
        sh '''
          set -euxo pipefail
          echo "DEBUG: WORKSPACE=$WORKSPACE"
          pwd
          ls -la
          # If this fails, you're not in the repo dir
          test -d .git
          git status
        '''
      }
    }

    stage('Continue') {
      steps {
        echo "Checkout fixed. Put your build/train commands after this."
      }
    }
  }

  post {
    always {
      sh '''
        set +e
        echo "POST DEBUG:"
        echo "WORKSPACE=$WORKSPACE"
        pwd
        ls -la
        if [ -d .git ]; then
          git rev-parse --is-inside-work-tree
          git rev-parse HEAD
        else
          echo "NO .git in current dir during post"
        fi
      '''
    }
  }
}
