import pathlib
import shutil
import subprocess
from typing import Literal

from typing_extensions import assert_never


def generate(dev_path: pathlib.Path, mode: Literal["solution", "release"]) -> None:
    print(f"Generating {mode} for {dev_path}")
    lines = dev_path.read_text().split("\n")
    out_lines = []

    state: Literal["common", "solution_lines", "release_lines"] = "common"
    indents = 0

    for l in lines:
        if state == "solution_lines":
            if l == " " * indents + "else:":
                print("\tentering release block")
                state = "release_lines"
                continue
            elif len(l) - len(l.lstrip()) <= indents and len(l.strip()) > 0:
                print("\texiting solution block")
                state = "common"
            elif mode == "solution":
                out_lines.append(l[4:])
                continue
            else:
                continue

        if state == "release_lines":
            if len(l) - len(l.lstrip()) <= indents and len(l.strip()) > 0:
                print("\texiting release block")
                state = "common"
            elif mode == "release":
                out_lines.append(l[4:])
                continue
            else:
                continue

        if state == "common":
            if l.strip() == "SOLUTION = True":
                continue
            elif l.strip() == "if SOLUTION:":
                print("\tfound solution block")
                state = "solution_lines"
                indents = len(l) - len(l.lstrip())
                continue
            else:
                out_lines.append(l)
                continue

        assert_never(state)

    out_path = dev_path.parent.parent / mode / dev_path.name
    out_path.write_text("\n".join(out_lines))
    print(f"Wrote to {out_path}")


def main() -> None:
    for mode in ("release", "solution"):
        root = pathlib.Path("./" + mode)
        if root.exists():
            shutil.rmtree(root)
        pathlib.Path(root).mkdir(exist_ok=True)

        generate(pathlib.Path("./dev/robot_part_1.py"), mode)
        print()
        generate(pathlib.Path("./dev/robot_part_2.py"), mode)

        for copy_filename in ("simulator.py", "requirements.txt", "redisgl"):
            copy_path = pathlib.Path("./dev/") / copy_filename
            new_path = root / copy_filename
            print(f"Copying {copy_path} to {new_path}")
            assert copy_path.exists()
            if copy_path.is_dir():
                shutil.copytree(copy_path, new_path)
            else:
                shutil.copy(copy_path, new_path)

        subprocess.call(["isort", mode])
        subprocess.call(["black", mode])


if __name__ == "__main__":
    main()
