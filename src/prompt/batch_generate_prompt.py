"""
Template renderer script that uses Jinja2 to generate prompts from templates.
Uses variables from template_vars.py and commit info from get_commit_info.py.
"""

import os
import subprocess
import sys
import time
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any
from tqdm import tqdm

# # Add the current directory to the path to import our modules
# sys.path.append(os.path.dirname(__file__))

from util.template_vars import get_template_variables, update_template_vars_with_commit_info
from util.get_commit_info import CommitInfoFetcher

from pymigbench.database import Database
from pathlib import Path


def render_template(template_path: str, variables: Dict[str, Any]) -> str:
    """
    Render a Jinja2 template with the provided variables.
    
    Args:
        template_path: Path to the template file
        variables: Dictionary of template variables
        
    Returns:
        Rendered template as string
    """
    # Get template directory and filename
    template_dir = os.path.dirname(template_path)
    template_name = os.path.basename(template_path)
    
    # Create Jinja2 environment
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    
    # Render template
    return template.render(**variables)


def generate_prompt(repo_name: str, commit_sha: str,
                   repo_base_folder: str, output_base_folder: str,
                   template_path: str, github_token: str = None) -> str:
    """
    Generate a prompt by rendering the template with repository and commit information.
    
    Args:
        repo_name: Repository name
        commit_sha: Commit SHA
        repo_base_folder: Base folder containing repositories
        output_base_folder: Base folder for output files
        template_path: Path to the Jinja2 template
        github_token: GitHub API token (optional, uses GITHUB_TOKEN env var if not provided)
        
    Returns:
        Rendered prompt as string
    """
    # Get base template variables
    template_vars = get_template_variables(repo_name, commit_sha, 
                                         repo_base_folder, output_base_folder)
    
    # Get commit information if GitHub token is available
    if github_token or os.getenv("GITHUB_TOKEN"):
        token = github_token or os.getenv("GITHUB_TOKEN")
        fetcher = CommitInfoFetcher(token)
        commit_info = fetcher.get_commit_info(f"{repo_name}", commit_sha)
        
        # Update template variables with commit info
        template_vars = update_template_vars_with_commit_info(template_vars, commit_info)
    
    # Render template
    return render_template(template_path, template_vars)


def main():
    """
    Example usage of the prompt generator.
    """
    yaml_root = Path("examples/pymigbench-yaml")

    db = Database.load_from_dir(yaml_root)
    migs = db.migs()

    for i, mig in tqdm(enumerate(migs)):
        if (i + 1) // 40 == 0:
            time.sleep(2)

        repo_name = mig.repo
        commit_sha = mig.commit

        repo_base_folder = "examples/repos"
        output_base_folder = "examples/envs"
        output_prompt_path = f"examples/prompts/{repo_name.replace('/', '_')}__{commit_sha}/prompt.md"
        template_path = "prompts/infer_env.md"
        
        # Generate and print the prompt
        try:
            prompt = generate_prompt(repo_name, commit_sha,
                                repo_base_folder, output_base_folder, template_path)
            os.makedirs(os.path.dirname(output_prompt_path))
            with open(output_prompt_path, "w") as f:
                f.write(prompt)
        except Exception as e:
            print(f"Error generating prompt: {e}", file=sys.stderr)
            continue


if __name__ == "__main__":
    main()
