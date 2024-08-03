from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .subproject import SubProject


@dataclass(frozen=True)
class ProjectPath:
    root: Path
    data_original: Path


# TODO: Implement to original Project class
class Project:
    _root_dir: Path
    subprojects: dict[str, SubProject]

    def __init__(self, root: str | Path):
        root = Path(root)
        if not (root / "ebilab.ini").exists():
            raise Exception("ebilab project directory not exist.")

        self._root_dir = root
        self.subprojects = self._find_subprojects()

    @property
    def path(self) -> ProjectPath:
        """
        Information about filepath of project
        """
        return ProjectPath(
            root=self._root_dir,
            data_original=self._root_dir / "data" / "original",
        )

    def _find_subprojects(self) -> dict[str, SubProject]:
        subprojects: dict[str, SubProject] = {}
        for item in self.path.root.iterdir():
            if item.is_dir():
                if (item / "ebilab.sub.yml").exists():
                    sub_project = SubProject(item)
                    subprojects[item.name] = sub_project
        return subprojects

    def get_original_files(self) -> list[Path]:
        """
        Get list of original data files
        """
        return [path for path in self.path.data_original.rglob("*.csv")]


def _get_current_project() -> Project:
    _paths = [Path(".").resolve()] + list(Path(".").resolve().parents)
    for path in _paths:
        root = path
        if (root / "ebilab.ini").exists():
            break
    else:
        raise Exception("Could not ebilab project data directory.")
    return Project(root)


_current_project: Project | None = None


def get_current_project() -> Project:
    """
    Search project file and return project class
    """

    global _current_project
    if _current_project:
        return _current_project
    _current_project = _get_current_project()
    return _current_project
