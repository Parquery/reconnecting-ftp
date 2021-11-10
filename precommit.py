#!/usr/bin/env python3
"""
Runs precommit checks on the repository.
"""
import argparse
import concurrent.futures
import hashlib
import pathlib
import subprocess
import sys
from typing import List, Union, Tuple  # pylint: disable=unused-import

import os
import yapf.yapflib.yapf_api


def compute_hash(text: str) -> str:
    """
    :param text: to hash
    :return: hash digest
    """
    md5 = hashlib.md5()
    md5.update(text.encode())
    return md5.hexdigest()


class Hasher:
    """
    Hashes the source code files and reports if they differed since the last hashing.
    """

    def __init__(self, source_dir: pathlib.Path, hash_dir: pathlib.Path) -> None:
        self.source_dir = source_dir
        self.hash_dir = hash_dir

    def __hash_path(self, path: pathlib.Path) -> pathlib.Path:
        """
        :param path: to a source file
        :return: path to the file holding the hash of the source text
        """
        if self.source_dir not in path.parents:
            raise ValueError(f"Expected the path to be beneath "
                             f"the source directory {str(self.source_dir)!r}, "
                             f"got: {str(path)!r}")

        return self.hash_dir / path.relative_to(self.source_dir).parent / (path.name + ".md5")

    def hash_differs(self, path: pathlib.Path) -> bool:
        """
        :param path: to the source file
        :return: True if the hash of the content differs to the previous hashing.
        """
        hash_pth = self.__hash_path(path=path)

        if not hash_pth.exists():
            return True

        with path.open('rt') as fid:
            txt = fid.read()

        new_hsh = compute_hash(text=txt)

        with hash_pth.open('rt') as fid:
            old_hsh = fid.read()

        return new_hsh != old_hsh

    def update_hash(self, path: pathlib.Path) -> None:
        """
        Hashes the file content and stores it on disk.

        :param path: to the source file
        :return:
        """
        hash_pth = self.__hash_path(path=path)
        hash_pth.parent.mkdir(parents=True, exist_ok=True)

        with path.open('rt') as fid:
            txt = fid.read()

        new_hsh = compute_hash(text=txt)

        with hash_pth.open('wt') as fid:
            fid.write(new_hsh)


def check(path: pathlib.Path, py_dir: pathlib.Path, overwrite: bool) -> Union[None, str]:
    """
    Runs all the checks on the given file.

    :param path: to the source file
    :param py_dir: path to src/py
    :param overwrite: if True, overwrites the source file in place instead of reporting that it was not well-formatted.
    :return: None if all checks passed. Otherwise, an error message.
    """
    style_config = py_dir / 'style.yapf'

    report = []

    # yapf
    if not overwrite:
        formatted, _, changed = yapf.yapflib.yapf_api.FormatFile(
            filename=str(path), style_config=str(style_config), print_diff=True)

        if changed:
            report.append(f"Failed to yapf {path}:\n{formatted}")
    else:
        yapf.yapflib.yapf_api.FormatFile(filename=str(path), style_config=str(style_config), in_place=True)

    # mypy
    with subprocess.Popen(
        ['mypy', str(path), '--ignore-missing-imports'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True) as proc:
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            report.append(f"Failed to mypy {path}:\nOutput:\n{stdout}\n\nError:\n{stderr}")

    # pylint
    with subprocess.Popen(
        ['pylint', str(path), '--rcfile={}'.format(py_dir / 'pylint.rc')],  # pylint: disable=consider-using-f-string
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True) as proc:
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            report.append(f"Failed to pylint {path}:\nOutput:\n{stdout}\n\nError:\n{stderr}")

    if len(report) > 0:
        return "\n".join(report)

    return None


def main() -> int:
    """"
    Main routine
    """
    # pylint: disable=too-many-locals
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        help="Overwrites the unformatted source files with the well-formatted code in place. "
        "If not set, an exception is raised if any of the files do not conform to the style guide.",
        action='store_true')
    args = parser.parse_args()

    overwrite = args.overwrite
    assert isinstance(overwrite, bool)

    py_dir = pathlib.Path(os.path.realpath(__file__)).parent

    hash_dir = py_dir / '.precommit_hashes'
    hash_dir.mkdir(exist_ok=True)

    hasher = Hasher(source_dir=py_dir, hash_dir=hash_dir)

    pths = sorted(list(py_dir.glob("*.py")) + list((py_dir / 'tests').glob("*.py")))

    # see which files changed:
    changed_pths = []  # type: List[pathlib.Path]
    for pth in pths:
        if hasher.hash_differs(path=pth):
            changed_pths.append(pth)

    if len(changed_pths) == 0:
        print("No file changed since the last pre-commit check.")
        return 0

    print(f"There are {len(changed_pths)} file(s) that need to be checked...")

    success = True

    futures_paths = []  # type: List[Tuple[concurrent.futures.Future, pathlib.Path]]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for pth in changed_pths:
            future = executor.submit(check, path=pth, py_dir=py_dir, overwrite=overwrite)
            futures_paths.append((future, pth))

        for future, pth in futures_paths:
            report = future.result()
            if report is None:
                print(f"Passed all checks: {pth}")
                hasher.update_hash(path=pth)
            else:
                print(f"One or more checks failed for {pth}:\n{report}")
                success = False

    print("Running unit tests...")
    return_code = subprocess.call([sys.executable, '-m', 'unittest', 'discover', str(py_dir / 'tests')])
    success = success and return_code == 0

    if not success:
        print("One or more checks failed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
