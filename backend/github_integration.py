import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from github import Github, GithubException
from git import Repo, GitCommandError
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

class GitHubIntegration:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.github_client = None
        self.repo_name = "tweet-tracker-backups"
        self.repo_full_name = None
        self.local_repo_path = None
        
        if self.github_token:
            try:
                self.github_client = Github(self.github_token)
                logger.info("GitHub client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GitHub client: {e}")
        else:
            logger.warning("No GitHub token provided - GitHub features disabled")

    async def initialize_repository(self, username: str) -> bool:
        """Initialize or connect to GitHub repository for backups"""
        try:
            if not self.github_client:
                logger.error("GitHub client not initialized")
                return False
            
            self.repo_full_name = f"{username}/{self.repo_name}"
            
            try:
                # Try to get existing repository
                repo = self.github_client.get_repo(self.repo_full_name)
                logger.info(f"Connected to existing repository: {self.repo_full_name}")
            except GithubException:
                # Create new repository
                user = self.github_client.get_user()
                repo = user.create_repo(
                    self.repo_name,
                    description="Tweet Tracker application backups and versions",
                    private=True,
                    auto_init=True
                )
                logger.info(f"Created new repository: {self.repo_full_name}")
            
            return True
        except Exception as e:
            logger.error(f"Error initializing repository: {e}")
            return False

    async def create_backup(self, app_data: Dict[str, Any], version_tag: str) -> Dict[str, Any]:
        """Create a backup of app data to GitHub"""
        try:
            if not self.github_client or not self.repo_full_name:
                raise ValueError("GitHub not properly initialized")
            
            repo = self.github_client.get_repo(self.repo_full_name)
            
            # Prepare backup data
            backup_data = {
                "version": version_tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "app_data": app_data,
                "metadata": {
                    "total_accounts": len(app_data.get('tracked_accounts', [])),
                    "total_name_alerts": len(app_data.get('name_alerts', [])),
                    "total_ca_alerts": len(app_data.get('ca_alerts', [])),
                    "backup_size_bytes": len(json.dumps(app_data)),
                }
            }
            
            # Convert to JSON
            backup_json = json.dumps(backup_data, indent=2, default=str)
            
            # Create file path
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            file_path = f"backups/{timestamp}_{version_tag}.json"
            
            # Create or update file in repository
            try:
                # Try to get existing file
                existing_file = repo.get_contents(file_path)
                repo.update_file(
                    file_path,
                    f"Update backup: {version_tag}",
                    backup_json,
                    existing_file.sha
                )
            except GithubException:
                # File doesn't exist, create new
                repo.create_file(
                    file_path,
                    f"Create backup: {version_tag}",
                    backup_json
                )
            
            # Create a release/tag for major versions
            try:
                repo.create_git_tag_and_release(
                    tag=f"v{timestamp}",
                    tag_message=f"Tweet Tracker backup: {version_tag}",
                    release_name=f"Backup {version_tag}",
                    release_message=f"Automatic backup created on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
                    object=repo.get_branch("main").commit.sha,
                    type="commit"
                )
            except:
                pass  # Tags are optional
            
            logger.info(f"Successfully created GitHub backup: {file_path}")
            
            return {
                "success": True,
                "file_path": file_path,
                "repository": self.repo_full_name,
                "backup_size": len(backup_json),
                "timestamp": timestamp
            }
        except Exception as e:
            logger.error(f"Error creating GitHub backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups from GitHub"""
        try:
            if not self.github_client or not self.repo_full_name:
                return []
            
            repo = self.github_client.get_repo(self.repo_full_name)
            
            # Get all files in backups directory
            try:
                contents = repo.get_contents("backups")
                if not isinstance(contents, list):
                    contents = [contents]
            except GithubException:
                # No backups directory yet
                return []
            
            backups = []
            for content in contents:
                if content.name.endswith('.json'):
                    try:
                        # Get file content
                        file_content = repo.get_contents(content.path)
                        backup_data = json.loads(file_content.decoded_content.decode('utf-8'))
                        
                        backups.append({
                            "filename": content.name,
                            "path": content.path,
                            "version": backup_data.get("version", "Unknown"),
                            "timestamp": backup_data.get("timestamp"),
                            "metadata": backup_data.get("metadata", {}),
                            "size": content.size,
                            "sha": content.sha
                        })
                    except Exception as e:
                        logger.error(f"Error reading backup file {content.name}: {e}")
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return backups
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    async def restore_backup(self, backup_path: str) -> Dict[str, Any]:
        """Restore app data from a GitHub backup"""
        try:
            if not self.github_client or not self.repo_full_name:
                raise ValueError("GitHub not properly initialized")
            
            repo = self.github_client.get_repo(self.repo_full_name)
            
            # Get backup file
            file_content = repo.get_contents(backup_path)
            backup_data = json.loads(file_content.decoded_content.decode('utf-8'))
            
            # Extract app data
            app_data = backup_data.get("app_data", {})
            
            logger.info(f"Successfully restored backup from: {backup_path}")
            
            return {
                "success": True,
                "app_data": app_data,
                "version": backup_data.get("version"),
                "timestamp": backup_data.get("timestamp"),
                "metadata": backup_data.get("metadata", {})
            }
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup from GitHub"""
        try:
            if not self.github_client or not self.repo_full_name:
                return False
            
            repo = self.github_client.get_repo(self.repo_full_name)
            
            # Get file to delete
            file_content = repo.get_contents(backup_path)
            
            # Delete file
            repo.delete_file(
                backup_path,
                f"Delete backup: {backup_path}",
                file_content.sha
            )
            
            logger.info(f"Successfully deleted backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            return False

    async def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        try:
            if not self.github_client or not self.repo_full_name:
                return {}
            
            repo = self.github_client.get_repo(self.repo_full_name)
            
            stats = {
                "repository_name": repo.full_name,
                "repository_url": repo.html_url,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "size": repo.size,
                "language": repo.language,
                "private": repo.private,
                "total_commits": repo.get_commits().totalCount,
                "total_releases": repo.get_releases().totalCount,
                "total_files": len(list(repo.get_contents("")))
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting repository stats: {e}")
            return {}