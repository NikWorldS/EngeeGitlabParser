import argparse
import asyncio
import time

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TaskID
)

from services.async_parser import Parser, WorkType
from services.async_downloader import Downloader


DEFAULT_SUMMARIZE_OPTION = False


def parse_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        description="Downloads Engee project from `EngeeGitlab` with `.engee` models."
    )
    arg_parser.add_argument(
        "-d",
        "--describe_models",
        type=bool,
        help=f"Sends a downloaded files to LLM for their describing if `True` (on default: {DEFAULT_SUMMARIZE_OPTION})."
    )

    return arg_parser.parse_args()


def make_progress_callback(progress: Progress, task_id: TaskID):
    def update_progress(advance: int):
        progress.update(task_id=task_id, advance=advance)
    return update_progress

async def main():
    console = Console()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    progress.start()

    parser = Parser(
        work_type=WorkType.CHECK_PROJECTS,
    )

    parser_task_id = progress.add_task(
        "[cyan]Parsing Engee Project...[/cyan]",
        total=parser.get_last_project_id()
    )

    parser.set_on_progress(make_progress_callback(progress, parser_task_id))

    console.log("Parsing process started...")

    result = await parser.main()
    progress.stop()

    console.log(f"Project parsing ended...")
    console.log(f"Caught links: {parser.get_links_count()}")

if __name__ == "__main__":
    asyncio.run(main())