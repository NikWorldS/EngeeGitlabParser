from services.converter import convert_models


BASE_RUN_PATH = "runs/"
CURRENT_RUN_DIR_PATH = "2026-04-23_165831/"

result = convert_models(
    input_dir=BASE_RUN_PATH + CURRENT_RUN_DIR_PATH + 'models/',
    output_dir=BASE_RUN_PATH + CURRENT_RUN_DIR_PATH + 'mds/',
    on_progress=lambda _: print('.', end='', flush=True),
)

print(f'\ntotal={result.total} success={result.success} skipped={result.skipped} failed={result.failed}')
