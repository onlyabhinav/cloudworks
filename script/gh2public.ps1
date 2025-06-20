# GitHub Repository Visibility Changer
# Usage: .\Change-GitHubRepoVisibility.ps1

# Prompt for repository path (OWNER/REPO)
$repo = "onlyabhinav/cloudworks"
$visibility = "public"

# Prompt for desired visibility
# $visibility = Read-Host "Enter the new visibility (public/private):"
# while ($visibility -ne "public" -and $visibility -ne "private") {
#     $visibility = Read-Host "Please enter either 'public' or 'private':"
# }

# Inform user about consequences
Write-Host "Changing repository visibility to $visibility can have unexpected consequences, including:"
Write-Host "- Losing stars and watchers"
Write-Host "- Detaching public forks"
Write-Host "- Disabling push rulesets"
Write-Host "- Allowing access to GitHub Actions history and logs"
Write-Host ""

# Execute gh command
gh repo edit $repo --visibility=$visibility
if ($?) {
    Write-Host "Repository visibility changed successfully to $visibility."
} else {
    Write-Host "Failed to change repository visibility. Please check your permissions and try again."
}


# # Ask for confirmation
# $confirm = Read-Host "Are you sure you want to proceed? (y/n):"
# if ($confirm -eq "y" -or $confirm -eq "Y") {
#     # Execute gh command
#     gh repo edit $repo --visibility=$visibility
#     if ($?) {
#         Write-Host "Repository visibility changed successfully to $visibility."
#     } else {
#         Write-Host "Failed to change repository visibility. Please check your permissions and try again."
#     }
# } else {
#     Write-Host "Operation cancelled."
# }
