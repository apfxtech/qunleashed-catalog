"""The catalog's CI in one command line, a command per step of a workflow:

  pull-request  changed, check, report
  app-stream    sync-ofw, pin
  publish       categories, changed, publish, withdraw, report, settled
  bootstrap     categories, stale, publish, report

check is also what an author runs before sending a pull request. Each
command loads only what it needs, so a step that only reads the
repository does without Pillow and ufbt."""

import argparse
import glob
import json
import sys
from pathlib import Path


def cmd_changed(args) -> int:
    from flipp_catalog.manifests import batches, changed
    changes, deleted = changed(args.base, args.head)
    print(json.dumps({"changed": changes, "batches": batches(changes, args.batch), "deleted": deleted}))
    return 0


def cmd_check(args) -> int:
    from flipp_catalog.check import check
    from flipp_catalog.report import Report
    return 1 if check(args.manifests, Report(args.report), build=args.build, offline=args.offline,
                      timeout=args.timeout) else 0


def cmd_publish(args) -> int:
    from flipp_catalog.publishing import publish
    from flipp_catalog.report import Report
    return 1 if publish(args.manifests, Report(args.report)) else 0


def cmd_categories(args) -> int:
    from flipp_catalog import server
    refused = 0
    for base in server.servers():
        status, text = server.put_categories(base)
        if status == 200:
            print(f"categories sent to {server.host(base)}: {text}")
        else:
            print(f"::error::{server.host(base)} answered {status} to categories.yml: {text[:1000]}")
            refused += 1
    return 1 if refused else 0


def cmd_withdraw(args) -> int:
    from flipp_catalog.publishing import withdraw
    from flipp_catalog.report import Report
    return 1 if withdraw(args.manifests, Report(args.report)) else 0


def cmd_sync_ofw(args) -> int:
    from flipp_catalog.stream import sync_ofw
    sync_ofw(Path(args.upstream))
    return 0


def cmd_pin(args) -> int:
    from flipp_catalog.stream import pin
    pin()
    return 0


def cmd_stale(args) -> int:
    from flipp_catalog.bootstrap import stale
    from flipp_catalog.manifests import batches
    paths = stale(args.mode)
    print(json.dumps({"count": len(paths), "batches": batches(paths, args.batch)}))
    return 0


def cmd_report(args) -> int:
    from flipp_catalog.report import Report, markdown
    print(markdown(args.title, Report.load(_files(args.reports))))
    return 0


def cmd_settled(args) -> int:
    from flipp_catalog.report import settled
    return 0 if settled(_files(args.reports), args.expect) else 1


def _files(patterns: list[str]) -> list[str]:
    return sorted({path for pattern in patterns for path in glob.glob(pattern)})


def main() -> int:
    parser = argparse.ArgumentParser(prog="publish.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("changed", help="manifests changed and deleted between two commits")
    p.add_argument("base")
    p.add_argument("head")
    p.add_argument("--batch", type=int, default=10)
    p.set_defaults(func=cmd_changed)
    p = sub.add_parser("check", help="every rule, and a ufbt build outside trusted.yml")
    p.add_argument("--offline", action="store_true", help="the manifest alone, nothing fetched")
    p.add_argument("--build", action="store_true", help="build entries outside trusted.yml with ufbt")
    p.add_argument("--timeout", type=int, default=60, help="seconds a ufbt build may take")
    p.add_argument("--report")
    p.add_argument("manifests", nargs="+")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("publish", help="assemble and send to the catalog server")
    p.add_argument("--report")
    p.add_argument("manifests", nargs="*")
    p.set_defaults(func=cmd_publish)
    p = sub.add_parser("categories", help="send categories.yml to every catalog server")
    p.set_defaults(func=cmd_categories)
    p = sub.add_parser("withdraw", help="take the entries of deleted manifests out of the catalog")
    p.add_argument("--report")
    p.add_argument("manifests", nargs="+")
    p.set_defaults(func=cmd_withdraw)
    p = sub.add_parser("sync-ofw", help="take in the official catalog's manifests we have none of or hold an older copy of")
    p.add_argument("upstream", help="a checkout of flipper-application-catalog")
    p.set_defaults(func=cmd_sync_ofw)
    p = sub.add_parser("pin", help="pin entries of trusted repositories to their latest commit")
    p.set_defaults(func=cmd_pin)
    p = sub.add_parser("stale", help="what bootstrap sends to the catalog server")
    p.add_argument("--mode", choices=("update", "force"), required=True)
    p.add_argument("--batch", type=int, default=20)
    p.set_defaults(func=cmd_stale)
    p = sub.add_parser("report", help="the reports of a run as Markdown")
    p.add_argument("--title", required=True)
    p.add_argument("reports", nargs="*")
    p.set_defaults(func=cmd_report)
    p = sub.add_parser("settled", help="exit 0 when every job reported and nothing waits for a retry")
    p.add_argument("--expect", type=int, required=True)
    p.add_argument("reports", nargs="*")
    p.set_defaults(func=cmd_settled)
    args = parser.parse_args()
    from flipp_catalog import BundlerException
    try:
        return args.func(args)
    except BundlerException as e:
        print(f"::error::{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
