"""
Variable provider for Jinja2 template rendering.
Defines all variables needed for the infer_env.md template.
"""

import os
from typing import Dict, Any


def get_template_variables(repo_name: str, commit_sha: str, 
                         repo_base_folder: str, output_base_folder: str) -> Dict[str, Any]:
    """
    Generate all Jinja2 variables needed for the infer_env.md template.
    
    Args:
        repo_name: Repository name
        commit_sha: Commit SHA
        repo_base_folder: Base folder containing repositories
        output_base_folder: Base folder for output files
        
    Returns:
        Dictionary containing all template variables
    """
    # Build paths using provided base folders
    repo_prefix = repo_name.replace('/', '_')
    repo_path = os.path.join(repo_base_folder, f"{repo_prefix}__{commit_sha}")
    output_dir = os.path.join(output_base_folder, f"{repo_prefix}__{commit_sha}")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    template_vars = {
        # Repository context
        "repo_name": f"{repo_name}",
        "commit_sha": commit_sha,
        "commit_ts": None,  # Will be filled by commit info
        "max_python_ver": None,  # Will be filled by commit info
        
        # Output file paths
        "success_path": os.path.join(output_dir, "_SUCCESS"),
        "failure_path": os.path.join(output_dir, "_FAILURE"), 
        "summary_path": os.path.join(output_dir, "summary.md"),
        "dockerfile_path": os.path.join(output_dir, "Dockerfile"),
        "run_instructions_path": os.path.join(output_dir, "run_instructions.sh"),
        
        # Input repository path
        "repo_path": repo_path,
    }
    
    return template_vars


def update_template_vars_with_commit_info(template_vars: Dict[str, Any], commit_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update template variables with commit information.
    
    Args:
        template_vars: Base template variables
        commit_info: Commit information from get_commit_info.py
        
    Returns:
        Updated template variables
    """
    updated_vars = template_vars.copy()
    
    if commit_info.get("timestamp"):
        updated_vars["commit_ts"] = commit_info["timestamp"].isoformat() + "Z"
    
    if commit_info.get("python_upper_bound"):
        major, minor = commit_info["python_upper_bound"]
        updated_vars["max_python_ver"] = f"{major}.{minor}"
    
    return updated_vars
