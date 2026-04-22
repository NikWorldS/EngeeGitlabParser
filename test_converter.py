from services.converter import convert_models

result = convert_models(
    input_dir='runs/2026-04-22_151318/models',
    output_dir='runs/2026-04-22_151318/mds',
    on_progress=lambda _: print('.', end='', flush=True),
)

print(f'\ntotal={result.total} success={result.success} skipped={result.skipped} failed={result.failed}')
