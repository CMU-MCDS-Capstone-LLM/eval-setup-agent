from pathlib import Path
from typing import List

from .jinja_env import make_env

from ..utils.logging import get_logger

logger = get_logger()


def render_from_path(template_path: Path, vars_dict: dict) -> str:
    assert template_path.is_file(), "template_path must be a file!"
    env = make_env(template_path.parent)
    tpl = env.get_template(template_path.name)
    output = tpl.render(**vars_dict)
    return output


def render_and_save(output_paths: List[Path], template_path: Path, vars_dict: dict, mode: int | None):
    """
    Search `template_filename` under `templates_dir`, render template using `vars_dict`,
    save in all paths in `output_paths` in an optional `mode`.

    Return the rendered text
    """
    logger.debug(f"Render from jinja template at {template_path}")
    logger.debug(f"Render with variables: {vars_dict}")

    if mode is not None:
        assert mode >= 0o000 and mode <= 0o777, f"Got invalid mode {oct(mode)}"

    output = render_from_path(template_path, vars_dict)

    for output_path in output_paths:
        logger.debug(f"Save rendered template at {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output)
        if mode is None:
            continue
        output_path.chmod(mode)

    return output
