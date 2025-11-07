from jinja2 import Template, Environment, StrictUndefined, FileSystemLoader
import os

templates_dir = os.path.dirname(__file__)

env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    undefined=StrictUndefined,
)

tpl = env.get_template("tpl.j2")
result = tpl.render(
    python_version_tag="3.11.13-slim", 
    mount_dir="/workspace", 
    repo_bind_src="repos/<myrepo>", 
    test_workdir="/workspace",
    app_user="appuser",
    project_apt_packages=["astgrep", "tree", "ripgrep"], 
    env_vars={"aaa": 111, "bbb": "bbb-222", "ccc": [1,2,3]},
    pip_deps=["numpy", "pandas", "mypackage==3.1.10"],
    install_editable=True, 
    test_cmd=["python", "-m", "pytest"]
)
with open("Dockerfile", "w") as file:
    file.write(result)
