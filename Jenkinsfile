// Release pipeline: build, unit tests, emulated-HIL smoke test, gate, promote.
// Stages only call make/tools, so the same steps run locally and in GitHub Actions.
pipeline {
    agent { label 'arm-toolchain' }
    options { timestamps(); buildDiscarder(logRotator(numToKeepStr: '50')) }
    parameters {
        choice(name: 'PROMOTE_TO', choices: ['nightly', 'candidate', 'release'],
               description: 'Channel to promote to if the gate passes')
    }

    stages {
        stage('Build') {
            steps { sh 'make clean fw' }
        }
        stage('Unit tests') {
            steps { sh 'make test-unit' }
            post { always { junit 'build/unit.xml' } }
        }
        stage('Smoke test (emulated Cortex-M3)') {
            // On real hardware this stage would flash an EVB on a HIL agent and read its UART.
            steps { sh 'make test-qemu' }
            post { always { junit 'build/qemu.xml' } }
        }
        stage('Manifest and changelog') {
            steps {
                sh 'make manifest changelog'
                archiveArtifacts artifacts: 'build/*.bin, build/manifest.json, build/CHANGELOG.md, build/fw.map'
            }
        }
        stage('Gate') {
            steps { sh 'make gate' }
        }
        stage('Promote') {
            when { anyOf { branch 'main'; buildingTag() } }
            steps { sh "python3 tools/promote.py --manifest build/manifest.json --to ${params.PROMOTE_TO}" }
        }
    }

    post {
        failure {
            // Name the first bad commit since the last green build and tell its author.
            script {
                def good = env.GIT_PREVIOUS_SUCCESSFUL_COMMIT
                if (good) {
                    def culprit = sh(script: "tools/bisect.sh ${good}", returnStdout: true).trim()
                    echo culprit
                    currentBuild.description = culprit
                }
            }
        }
    }
}
