<#
.SYNOPSIS
    Automates the process of committing and pushing changes to a Git repository using the gh-cli for authentication checks.
.DESCRIPTION
    This PowerShell script checks for staged changes (new, modified, deleted files)
    in the current Git repository, generates a dynamic commit message based on those
    changes, commits them, and then pushes the commit to the specified branch of the
    pre-configured remote repository. It is designed to run without user interaction.
.NOTES
    Author: Your Name
    Date: 20/06/2025
    Version: 1.2

    Prerequisites:
    - Git must be installed and accessible from the command line (in your PATH).
    - GitHub CLI ('gh') must be installed and you must be authenticated ('gh auth login').
    - The script must be run from within a Git repository.
    - A remote repository (like 'origin') must be configured and linked to a GitHub repository.
#>

# --- Configuration ---
# Set the name of the branch you want to push to.
$branchToPush = "main"
# Set the name of the remote repository.
$remoteName = "origin"

# --- Script Body ---

# Function to write a message to the console with a timestamp
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

Write-Log "Starting automated Git commit and push process..."

# 1. Check for required tools (Git and gh-cli)
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR: Git is not installed or not in your PATH. Aborting." -Level "ERROR"
    exit 1
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR: GitHub CLI ('gh') is not installed or not in your PATH. Please install it to use this script. Aborting." -Level "ERROR"
    exit 1
}

# Check if logged into gh. This helps ensure credentials are set up.
gh auth status > $null
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: You are not logged into the GitHub CLI. Please run 'gh auth login'. Aborting." -Level "ERROR"
    exit 1
}

Write-Log "Git and GitHub CLI are installed and configured."

# 2. Check if the current directory is a Git repository
if (-not (Test-Path ".git")) {
    Write-Log "ERROR: This script is not running inside a Git repository. Aborting." -Level "ERROR"
    exit 1
}

Write-Log "Git repository found."

# 3. Get the status of the repository to see what has changed
# The 'git status --porcelain' command gives a simple, script-friendly output.
$gitStatus = git status --porcelain

if ([string]::IsNullOrWhiteSpace($gitStatus)) {
    Write-Log "No changes to commit. Working tree is clean. Exiting."
    exit 0
}

Write-Log "Changes detected in the repository."

# 4. Generate a dynamic commit message based on file changes
# We will create a summary of added, modified, and deleted files.

$commitMessageLines = @("Automated commit: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$commitMessageLines += "" # Add a blank line for conventional commit format

# Parse the output of 'git status --porcelain'
$addedFiles = $gitStatus | Where-Object { $_.Trim().StartsWith("A") -or $_.Trim().StartsWith("??") } | ForEach-Object { "    - Added: " + ($_.Trim() -replace '^[AMDRCU\?\?]+\s+', '') }
$modifiedFiles = $gitStatus | Where-Object { $_.Trim().StartsWith("M") } | ForEach-Object { "    - Modified: " + ($_.Trim() -replace '^[AMDRCU\?\?]+\s+', '') }
$deletedFiles = $gitStatus | Where-Object { $_.Trim().StartsWith("D") } | ForEach-Object { "    - Deleted: " + ($_.Trim() -replace '^[AMDRCU\?\?]+\s+', '') }

if ($addedFiles.Count -gt 0) {
    $commitMessageLines += "New files:"
    $commitMessageLines += $addedFiles
}
if ($modifiedFiles.Count -gt 0) {
    $commitMessageLines += "Modified files:"
    $commitMessageLines += $modifiedFiles
}
if ($deletedFiles.Count -gt 0) {
    $commitMessageLines += "Deleted files:"
    $commitMessageLines += $deletedFiles
}

# Combine the lines into a single string for the commit command
$commitMessage = $commitMessageLines | Out-String

Write-Log "Generated Commit Message:"
Write-Host $commitMessage

# 5. Add all changes to the staging area
# 'git add .' stages all new, modified, and deleted files in the current directory.
Write-Log "Adding all changes to the staging area..."
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: 'git add' command failed. Aborting." -Level "ERROR"
    exit 1
}
Write-Log "Files staged successfully."

# 6. Commit the staged changes
# The -m flag allows us to pass the commit message directly.
Write-Log "Committing changes..."
git commit -m $commitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: 'git commit' command failed. This might happen if there was nothing to commit after all. Aborting." -Level "ERROR"
    exit 1
}
Write-Log "Changes committed successfully."

# 7. Push the changes to the remote repository using git
Write-Log "Pushing changes to remote '$remoteName' on branch '$branchToPush'..."
git push $remoteName $branchToPush
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: 'git push' command failed. Check your connection, credentials, and repository settings. Aborting." -Level "ERROR"
    exit 1
}

Write-Log "Changes pushed successfully to remote repository."
Write-Log "Process completed."
