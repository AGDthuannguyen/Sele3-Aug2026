pipeline {
    // Use a Windows agent for browser verification and Windows PowerShell steps.
    agent { label 'windows' }

    options {
        skipDefaultCheckout()
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    parameters {
        choice(name: 'BROWSER', choices: ['chrome', 'firefox', 'edge'],
               description: 'Browser for the public-site tests')
        string(name: 'BASE_URL', defaultValue: 'https://www.automationexercise.com/',
               description: 'URL of the browser test target')
        string(name: 'PAGE_LOAD_TIMEOUT', defaultValue: '60',
               description: 'Page-load timeout in seconds')
        string(name: 'ACTION_TIMEOUT', defaultValue: '10',
               description: 'Locator action timeout in seconds')
        string(name: 'ASSERTION_TIMEOUT', defaultValue: '5',
               description: 'Retrying assertion timeout in seconds')
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Install') {
            steps {
                powershell '''
                    poetry check --lock
                    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
                    poetry sync
                    exit $LASTEXITCODE
                '''
            }
        }

        stage('Unit and plugin tests') {
            steps {
                powershell '''
                    poetry run pytest -m "not browser" -n 2 -q --junitxml=artifacts/junit-unit.xml --alluredir=artifacts/allure-unit
                    exit $LASTEXITCODE
                '''
            }
        }

        stage('Browser tests') {
            steps {
                powershell '''
                    $pytestArgs = @(
                        '-m', 'browser', '-n', '2', '--headless', '--maxfail=1',
                        "--browser=$env:BROWSER", "--base-url=$env:BASE_URL",
                        "--page-load-timeout=$env:PAGE_LOAD_TIMEOUT",
                        "--action-timeout=$env:ACTION_TIMEOUT",
                        "--assertion-timeout=$env:ASSERTION_TIMEOUT",
                        '--junitxml=artifacts/junit-browser.xml',
                        '--alluredir=artifacts/allure-browser'
                    )
                    poetry run pytest @pytestArgs
                    exit $LASTEXITCODE
                '''
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'artifacts/junit-*.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'artifacts/**/*'
        }
    }
}
