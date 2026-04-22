import argparse
import asyncio
from datetime import datetime
import os

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

from services.async_parser import Parser
from services.async_downloader import Downloader
from services.converter import convert_models, get_api_key, ConversionResult

DEFAULT_DOWNLOAD_OPTION = False
DEFAULT_SUMMARIZE_OPTION = False
BASE_RUNS_DIRECTORY = "./runs"

def parse_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        description="Downloads Engee project from `EngeeGitlab` with `.engee` models."
    )
    arg_parser.add_argument(
        "-d",
        "--download",
        type=bool,
        help=f"Downloads files from gitlab if `True` (on default: {DEFAULT_SUMMARIZE_OPTION})."
    )

    return arg_parser.parse_args()

def setup() -> None:
    if not os.path.exists(BASE_RUNS_DIRECTORY):
        os.mkdir(BASE_RUNS_DIRECTORY)

def make_progress_callback(progress: Progress, task_id: TaskID):
    def update_progress(advance: float):
        progress.update(task_id=task_id, advance=advance)
    return update_progress

def __create_dir(dir_path: str) -> None:
    try:
        os.mkdir(dir_path)
        os.mkdir(dir_path + "/models")
        os.mkdir(dir_path + "/mds")
    except FileExistsError:
        pass

def get_current_run_dir_path() -> str:
    """
    :return: Путь к папке текущего запуска для сохранения файлов
    """
    datetime_now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dir_path = f"{BASE_RUNS_DIRECTORY}/{datetime_now}"
    __create_dir(dir_path)
    return dir_path

def _count_models(models_dir: str) -> int:
    if not os.path.exists(models_dir):
        return 0
    return sum(
        1 for f in os.listdir(models_dir)
        if f.lower().endswith(('.zip', '.engee'))
    )

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

    setup()
    run_dir_path = get_current_run_dir_path()

    parser = Parser(
        work_dir=run_dir_path,
    )
    downloader = Downloader(
        work_dir=run_dir_path,
    )

    parser_task_id = progress.add_task(
        "[cyan]Parsing repositories...[/cyan]",
        total=parser.get_last_project_id()
    )
    parser.set_on_progress(make_progress_callback(progress, parser_task_id))

    links = await parser.main()
    downloader.set_file_links(links)
    progress.update(
        task_id=parser_task_id,
        completed=parser.get_last_project_id(),
        description=f"[green]Parsing completed ([white]{len(links)}[/white] files found).[/green]",
    )

    downloader_task_id = progress.add_task(
        "[cyan]Downloading Engee models...[/cyan]",
        total=downloader.get_links_count(),
    )
    downloader.set_on_progress(make_progress_callback(progress, downloader_task_id))

    await downloader.main()
    progress.update(
        task_id=downloader_task_id,
        completed=downloader.get_links_count(),
        description=f"[green]Downloading completed.[/green]",
    )

    models_dir = run_dir_path + "/models"
    mds_dir = run_dir_path + "/mds"
    models_count = _count_models(models_dir)

    api_key = get_api_key()
    if not api_key:
        progress.stop()
        console.print("[yellow]OPENROUTER_API_KEY не найден — шаг конвертации пропущен.[/yellow]")
        console.print(f"[dim]Модели сохранены в: {os.path.abspath(models_dir)}[/dim]")
        return

    converter_task_id = progress.add_task(
        "[cyan]Converting models to Markdown...[/cyan]",
        total=max(models_count, 1),
    )

    result: ConversionResult = convert_models(
        input_dir=models_dir,
        output_dir=mds_dir,
        api_key=api_key,
        on_progress=make_progress_callback(progress, converter_task_id),
    )

    progress.update(
        task_id=converter_task_id,
        completed=models_count,
        description=(
            f"[green]Converting completed "
            f"([white]{result.success}[/white] ok, "
            f"[dim]{result.skipped}[/dim] skipped, "
            f"[red]{result.failed}[/red] failed).[/green]"
        ),
    )

    progress.stop()

if __name__ == "__main__":
    asyncio.run(main())
