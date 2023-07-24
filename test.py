git_repository="git@gitlab.fbsvc.bz:dotnet/LiveCenter-GUI/LiveCenter-Client.git"
scripts_git_repository="git@gitlab.fbsvc.bz:fb-sysadmins/rnd-deploy-win.git"
InstallerFileName="LiveCenterSetup"

if ("${Branch}" == "master") {
    configuration="Release"
    build_suffix=""
    threshold_type="failureThreshold"
    newthreshold_type="failureNewThreshold"
}
if ("${Branch}" == "master_test") {
    configuration="MasterTest"
    build_suffix="-mt"
    threshold_type="unstableThreshold"
    newthreshold_type="unstableNewThreshold"
}
if ("${Branch}" == "release_candidate") {
    configuration="Release_Candidate"
    build_suffix="-rc"
    threshold_type="unstableThreshold"
    newthreshold_type="unstableNewThreshold"
}
if ("${Branch}" == "test") {
    configuration="Debug"
    build_suffix="-test"
    threshold_type="unstableThreshold"
    newthreshold_type="unstableNewThreshold"
}



pipeline {
    agent {
        node { 
            label 'dotwin' 
        } 
    } 
    stages {
        stage ('Get source'){
            steps () {
                    cleanWs()
                    checkout([$class: 'GitSCM', branches: [[name: '$Branch']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: '39c35701-7360-44a1-829d-d789133bd14f', url: "$git_repository"]]])
                    script{
                        shortCommit = bat (returnStdout: true, script: "C:\\ProgramData\\Git\\bin\\git.exe rev-parse HEAD").split("\n")[2].trim()
                    env.GIT_COMMIT = shortCommit
                    }
            }
        }

        stage('Check version') {
            when {
                anyOf {
                        environment name: 'Branch', value: 'master'
                        environment name: 'Branch', value: 'release_candidate'
                }
            }
            steps {
                powershell returnStdout: true, script: '''### 
                    # by Stepan Solovyev 15/06/20
                    ###
                    # Description: 
                    # - parsing *.csproj files in directory for test nuget pkgs (by version, ex. 1.0.1 is prod package and  1.0.1alpha is test package)
                    # - checking if nuget pkgs are the same version at different csproj files
                    ###
                    # Call examle:
                    # -workdir "C:\\temp"
                    ###
                    # Exit codes:
                    # 0 - success, no test packages found
                    # 1 - failure, one or more test packages found
                    # 2 - wrong args or path does not exist
                    # 3 - different pkgs version found
                    ###
                    # Version 2
                    ###


                    # pass arguments to script with default value
                    #param([String]$workdir="") 
                    $workdir="$env:WORKSPACE\\src"  
                    # dedicated class with empty default field values 
                    # declaration to simplify future sort operations
                    class TableRecord {
                        [String] $FileName = ""
                        [String] $PkgName  = ""
                        [String] $Version  = ""

                        [String]GetInfo(){
                            return ($this.FileName+" "+$this.PkgName+" "+$this.Version)
                        }
                    }

                    # args and path validation 
                    if($workdir -eq [String]::Empty -and (Test-Path $workdir)){exit 2;}

                    # getting list of files 
                    $csprojs = Get-ChildItem $workdir -Filter "*.csproj" -Recurse

                    # string two dim array format is {filename, pkgname, version}
                    # slow but reliable
                    $Data = New-Object -TypeName "System.Collections.ArrayList"

                    # postpone to set exitcode to validate all files at once without script interrupting 
                    [int64]$exitcode = 0;

                    foreach($csproj in $csprojs){
                        [xml]$Xml = Get-Content $csproj.FullName

                        # case 1 & 2: xmlns & xmlversion not set
                        if($Xml.Project.NamespaceURI -eq [String]::Empty){

                            # case 1: xmlns & xmlversion not set AND //PackageReference[@Version] returns nothing
                            if((Select-Xml -xml $Xml -XPath "//PackageReference[@Version]").Count -eq 0){

                                # trying to read other XPATH AND excluding empty rows from $TempArray array
                                if((Select-Xml -xml $Xml -XPath "//Version").Count -ne 0){
                                    Select-Xml -xml $Xml -XPath "//Version" | foreach {`
                                        # temp var with empty string fields to future write to $data arraylist
                                        $TempArray = New-Object TableRecord

                                        # setting up row data one by one
                                        # project file name
                                        $TempArray.FileName = $csproj.Name;`

                                        # package name
                                        $TempArray.PkgName = $_.Node.ParentNode.Include;`

                                        # package version
                                        $TempArray.Version = $_.node.InnerText;
                                        
                                        # saving result to arraylist
                                        $Data.Add($TempArray)|Out-Null
                                        }
                                }
                                # (debug option) write filename to console if no packages found at current file at all
                                else{
                                    # debug purposes
                                    #write-host "WARNING: File contain no any package references: "$csproj.Name;
                                    continue;}}
                            else{
                                # case 2: xmlns & xmlversion not set AND //PackageReference[@Version] returns value
                                Select-Xml -xml $Xml -XPath "//PackageReference[@Version]" | foreach {`
                                # doing the same as case 1
                                
                                # temp var with empty string fields to future write to $data arraylist
                                $TempArray = New-Object TableRecord

                                $TempArray.FileName = $csproj.Name;`
                                $TempArray.Version = $_.node.Version;`
                                $TempArray.PkgName = $_.node.include;
                                # saving result to arraylist
                                $Data.Add($TempArray)|Out-Null}}}

                        # case 3: xmlns & xmlversion set correctly
                        else{
                            $Namespace = @{command = $Xml.Project.NamespaceURI}
                            select-xml -xml $Xml -XPath "//command:Version" -Namespace $Namespace | foreach {`
                            # temp var with empty string fields to future write to $data arraylist
                            $TempArray = New-Object TableRecord

                            $TempArray.FileName = $csproj.Name;`
                            $TempArray.Version = $_.node.InnerXML;`
                            $TempArray.PkgName = $_.Node.ParentNode.Include;
                            # saving result to arraylist
                            $Data.Add($TempArray)|Out-Null}}
                    }

                    # validation step 1: doing validation for characters existance using int64::Parse for version field
                    foreach($element in $Data){
                    $element.Version.Split(\'.\')|foreach {
                        try{[int64]::Parse($_)|out-null}
                        catch{write-host "not PROD pkg version found at "$element.getinfo();$exitcode = 1;}}
                    }

                    # validaton step 2: validation for pkgs version equality
                    # sorting objects by pkgname
                    $SortedArray = $data | Sort-Object -Property PkgName

                    for ($i = 0; $i -lt $SortedArray.Count; $i++)
                    { 
                        # if next element is diff pkg doing skip as well
                        if($SortedArray[$i].PkgName -ne $SortedArray[$i+1].PkgName){continue;}

                        # doing version comparsion with next element in array
                        if($SortedArray[$i].Version -ne $SortedArray[$i+1].Version){$exitcode = 3;
                            write-host $SortedArray[$i].GetInfo()" not equal "$SortedArray[$i+1].GetInfo()}  
                    }
                    exit $exitcode;'''
            } 
        }

        stage ('Set  version with build_number'){
            steps () {
                bat ('''
                powershell -command "((Get-Content .\\src\\LiveCenter\\Properties\\AssemblyVersion.cs) -replace '00000',%BUILD_NUMBER%) | set-content .\\src\\LiveCenter\\Properties\\AssemblyVersion.cs"
                ''')
            }
        }

        stage ('Build'){
            steps () {
                bat "dotnet nuget locals http-cache --clear"
                bat "\"${tool 'MsBuild 2022'}\" src\\LiveCenter.sln -t:restore /p:Configuration=${configuration} -verbosity:m"
                bat "\"${tool 'MsBuild 2022'}\" src\\LiveCenter.sln -t:rebuild /p:Configuration=${configuration} -verbosity:m"
            }
        }

        stage ('Change Jenkins Build Number'){
            steps () {
                script {
                    vers = bat (script: ".\\Build\\Utils\\ReadAssembly.exe .\\bin\\LiveCenter\\$configuration\\LiveCenter.exe", returnStdout: true).split(' ')[2].trim()
                    println(vers)
                    env.vers=vers
                    env.art_vers = vers+build_suffix
                    currentBuild.displayName = "${vers}${build_suffix}"
                }
            }  
        }

        stage ('Run tests'){
            steps () {
                bat encoding: 'cp866', script: "dotnet test %WORKSPACE%/src -l:trx; -r %WORKSPACE%/Reports --no-restore"
            }
        }
        stage ('Parsing tests'){
            steps () {
                xunit thresholds: [failed(failureThreshold: "0", unstableThreshold: "0")], tools: [MSTest(deleteOutputFiles: true, failIfNotNew: true, pattern: 'Reports\\*.trx', skipNoTestFiles: false, stopProcessingIfError: true)]            
            }
        }

        stage ('make installer'){
            steps () {
                bat ("""
                .\\Build\\Utils\\InnoSetup\\source\\iscc.exe /dSourceDir=..\\..\\..\\bin\\LiveCenter\\$configuration\\ /dAppVersion=$configuration /dAppConfiguration=$configuration /o.\\artifacts\\ /f$InstallerFileName .\\Build\\LiveCenter\\InnoSetup\\main.iss
                """)
            }
        }
        stage ('sign-installer'){
            steps () {
                bat ("""
                powershell -executionpolicy bypass -File c:\\psscripts\\sign-files.ps1 -Path %WORKSPACE%\\artifacts\
                """)
            }
        }
        
        stage ('Generate feed'){
            steps () {
                bat ("""
                .\\Build\\Utils\\FeedGenerator.exe file=.\\artifacts\\${env:InstallerFileName}.exe version=${env:vers}  feed=.\\artifacts\\feed.xml
                """)
            }
        }
        stage ('Make zip'){
            steps () {
                bat ("""
                echo ${env:GIT_COMMIT} >> %WORKSPACE%\\artifacts\\commitinfo
                powershell Compress-Archive -path %WORKSPACE%\\artifacts\\* -DestinationPath %WORKSPACE%\\artifacts\\Artifact.zip
                powershell (Get-FileHash artifacts\\Artifact.zip -Algorithm MD5).Hash > artifacts\\Artifact.zip.md5
                powershell (Get-FileHash artifacts\\Artifact.zip -Algorithm SHA1).Hash > artifacts\\Artifact.zip.sha1
                """)
            }
        }

        stage ('upload zip'){
            when {
                anyOf {
                        environment name: 'Branch', value: 'master'
                        environment name: 'Branch', value: 'master_test'
                        environment name: 'Branch', value: 'release_candidate'
                }
            }
            steps () {
                httpRequest authentication: '446beb45-cee2-41b4-b67d-57df7598ed31', httpMode: 'PUT', ignoreSslErrors: true, responseHandle: 'NONE', uploadFile: 'artifacts\\Artifact.zip', url: "https://nexus.fbsvc.bz/repository/dotnet_winbins/LiveCenter-Client/Client/${env:art_vers}/Client-${env:art_vers}.zip", wrapAsMultipart: false
                httpRequest authentication: '446beb45-cee2-41b4-b67d-57df7598ed31', httpMode: 'PUT', ignoreSslErrors: true, responseHandle: 'NONE', uploadFile: 'artifacts\\Artifact.zip.md5', url: "https://nexus.fbsvc.bz/repository/dotnet_winbins/LiveCenter-Client/Client/${env:art_vers}/Client-${env:art_vers}.zip.md5", wrapAsMultipart: false
                httpRequest authentication: '446beb45-cee2-41b4-b67d-57df7598ed31', httpMode: 'PUT', ignoreSslErrors: true, responseHandle: 'NONE', uploadFile: 'artifacts\\Artifact.zip.sha1', url: "https://nexus.fbsvc.bz/repository/dotnet_winbins/LiveCenter-Client/Client/${env:art_vers}/Client-${env:art_vers}.zip.sha1", wrapAsMultipart: false
            }
        }
        stage('Autodeploy') {
            when {
                expression { params.autodeploy == true }
            }
            steps {
                script {
                    if (env.Branch == "master") {    
                        build job: 'AnyWhiteLabel_PROD/dn/ANY_prod_LiveCenter-Client', 
                            parameters: [
                                string(name: 'version', value: "${env:art_vers}")
                            ]
                    }
                    if (env.Branch == "master_test") {    
                        build job: 'AnyWhiteLabel_TEST/dn/LiveCenter-Client', 
                            parameters: [
                                string(name: 'version', value: "${env:art_vers}")
                            ]
                    }
                    if (env.Branch == "release_candidate") {    
                        build job: 'AnyWhiteLabel_PROD/dn/ANY_prod_LiveCenter-Client-rc', 
                            parameters: [
                                string(name: 'version', value: "${env:art_vers}")
                            ]
                    }
                }            
            } 
        }
    }
    post {
        unstable {
            slackSend channel: '#sc_dotnet_releases', color: 'warning', iconEmoji: ':mega:', message: "${env.JOB_NAME} - #${env.BUILD_NUMBER} ${currentBuild.currentResult} after ${currentBuild.durationString.replace(' and counting', '')} (<${env.RUN_DISPLAY_URL}|Logs>) (<${env.BUILD_URL}/testReport|Test Result>)", teamDomain: 'knn-gd', tokenCredentialId: 'dotnet_slack-releases', username: 'jenkins'
        }
        failure {
            slackSend channel: '#sc_dotnet_releases', color: 'danger', iconEmoji: ':mega:', message: "${env.JOB_NAME} - #${env.BUILD_NUMBER} ${currentBuild.currentResult} after ${currentBuild.durationString.replace(' and counting', '')} (<${env.RUN_DISPLAY_URL}|Logs>) (<${env.BUILD_URL}/testReport|Test Result>)", teamDomain: 'knn-gd', tokenCredentialId: 'dotnet_slack-releases', username: 'jenkins'
        }
        aborted {
            slackSend channel: '#sc_dotnet_releases', color: 'grey', iconEmoji: ':mega:', message: "${env.JOB_NAME} - #${env.BUILD_NUMBER} ${currentBuild.currentResult} after ${currentBuild.durationString.replace(' and counting', '')} (<${env.RUN_DISPLAY_URL}|Logs>), (<${env.BUILD_URL}/testReport|Test Result>)", teamDomain: 'knn-gd', tokenCredentialId: 'dotnet_slack-releases', username: 'jenkins'
        }
    }
}