"""Create a private, uniquely named backup checkpoint and integrity receipt; never prune."""

import argparse
import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from taxi.manage import copy_database


def checkpoint(source, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.stat().st_mode & 0o077:
        raise ValueError("Backup directory must be owner-only; set permissions to 0700")
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)
    output = directory / (name + ".sqlite3")
    copy_database(source, output)
    receipt = {
        "backup": output.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "bytes": output.stat().st_size,
        "off_machine_copy_verified": False,
        "restore_drill_completed": False,
    }
    fd = os.open(directory / (name + ".json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="runtime/taxi.sqlite3")
    parser.add_argument("--directory", default="runtime/backups/checkpoints")
    args = parser.parse_args()
    print(f"Private checkpoint created: {checkpoint(args.source, args.directory)}")
