import os
import zipfile
import json
import requests
import time
from dataclasses import dataclass
from typing import Callable, Optional

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat"

SYSTEM_PROMPT = """Анализируй модель Engee. Создай техническое описание в Markdown:

1. Общее описание модели по именам блоков и сигналов
2. Используемые блоки с ключевыми параметрами
3. Логическая цепочка работы - как сигналы проходят через блоки
4. Структура модели и назначение подсистем

Формат:
- Только Markdown
- Заголовки: "Общее описание", "Используемые блоки", "Логическая цепочка", "Структура модели"

Только текст ТЗ в Markdown."""


@dataclass
class ConversionResult:
    total: int
    success: int
    skipped: int
    failed: int


def get_api_key() -> Optional[str]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.strip().startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip()

    return None


def _analyze_file(zf: zipfile.ZipFile, filename: str):
    try:
        with zf.open(filename) as f:
            data = json.load(f)

        # state — плоский словарь UUID→объект (не вложенный под 'objects')
        if 'state' in data and isinstance(data['state'], dict):
            objects = data['state']
        elif 'objects' in data:
            objects = data['objects']
        else:
            return [], []

        blocks = []
        lines = []

        for obj_id, obj in objects.items():
            if not isinstance(obj, dict):
                continue
            if obj.get('type') == 'block':
                params = obj.get('blockValues', {})
                blocks.append({
                    'id': obj_id,
                    'name': obj.get('blockName', f'Block_{obj_id[:8]}'),
                    'type': obj.get('blockType', ''),
                    'path': obj.get('blockPath', ''),
                    'params': params,
                })
            elif obj.get('type') == 'line':
                lines.append({
                    'from_block': obj.get('source', {}).get('block_id', ''),
                    'from_port': obj.get('source', {}).get('port_name', ''),
                    'to_block': obj.get('destination', {}).get('block_id', ''),
                    'to_port': obj.get('destination', {}).get('port_name', ''),
                })

        return blocks, lines

    except Exception:
        return [], []


def _extract_model_data(zip_path: str):
    try:
        file_name = os.path.basename(zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            all_files = zf.namelist()

            analysis = {
                'filename': file_name,
                'model_name': file_name.replace('.zip', '').replace('.engee', ''),
                'root_blocks': [],
                'root_lines': [],
                'subsystems': [],
                'total_blocks': 0
            }

            if 'model.json' in all_files:
                try:
                    with zf.open('model.json') as f:
                        model_data = json.load(f)
                        name = model_data.get('name', '')
                        if name:
                            analysis['model_name'] = name
                except Exception:
                    pass

            if 'root.json' in all_files:
                blocks, lines = _analyze_file(zf, 'root.json')
                analysis['root_blocks'] = blocks
                analysis['root_lines'] = lines
                analysis['total_blocks'] += len(blocks)

            for file in all_files:
                if (file.endswith('.json') and
                        file not in ['model.json', 'configset.json', 'root.json'] and
                        'model_inference' not in file):
                    blocks, lines = _analyze_file(zf, file)
                    if blocks:
                        analysis['subsystems'].append({
                            'filename': file,
                            'blocks': blocks[:20],
                            'lines': lines[:20],
                            'block_count': len(blocks)
                        })
                        analysis['total_blocks'] += len(blocks)

            return True, analysis, ""

    except Exception as e:
        return False, {}, f"Ошибка: {str(e)}"


def _prepare_data_for_prompt(analysis: dict) -> str:
    parts = []

    parts.append(f"Модель: {analysis['model_name']}")
    parts.append(f"Файл: {analysis['filename']}")
    parts.append(f"\nСтатистика:")
    parts.append(f"Всего блоков: {analysis['total_blocks']}")
    parts.append(f"Подсистем: {len(analysis['subsystems'])}")

    if analysis['root_blocks']:
        parts.append(f"\nБлоки основной схемы:")
        for block in analysis['root_blocks'][:20]:
            line = f"- [{block['type']}] {block['name']}"
            if block.get('path'):
                line += f"  (библиотека: {block['path']})"
            if block.get('params'):
                params_str = ', '.join(f"{k}={v}" for k, v in list(block['params'].items())[:5])
                line += f"  | параметры: {params_str}"
            parts.append(line)

    if analysis['root_lines']:
        id_to_name = {b['id']: b['name'] for b in analysis['root_blocks']}
        parts.append(f"\nСвязи основной схемы:")
        for line in analysis['root_lines'][:20]:
            src = id_to_name.get(line['from_block'], line['from_block'][:8])
            dst = id_to_name.get(line['to_block'], line['to_block'][:8])
            parts.append(f"- {src}.{line['from_port']} → {dst}.{line['to_port']}")

    if analysis['subsystems']:
        parts.append(f"\nПодсистемы:")
        for subsystem in analysis['subsystems']:
            parts.append(f"\n{subsystem['filename']}  (блоков: {subsystem['block_count']}):")
            for block in subsystem['blocks'][:5]:
                line = f"  - [{block['type']}] {block['name']}"
                if block.get('params'):
                    params_str = ', '.join(f"{k}={v}" for k, v in list(block['params'].items())[:3])
                    line += f"  | {params_str}"
                parts.append(line)

    return "\n".join(parts)


def _ask_ai(api_key: str, prompt_text: str, retries: int = 3):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.1,
        "max_tokens": 2000
    }

    last_error = ""
    for attempt in range(retries):
        try:
            response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=90)

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return True, result['choices'][0]['message']['content'], ""

            last_error = f"Ошибка API: {response.status_code}"

        except Exception as e:
            last_error = f"Ошибка: {str(e)}"

        if attempt < retries - 1:
            time.sleep(5 * (attempt + 1))

    return False, "", last_error


def _build_content(zip_file: str, analysis: dict, ai_ok: bool, ai_description: str, ai_error: str) -> str:
    if ai_ok:
        return f"""# Техническое описание модели Engee

**Файл:** {zip_file}
**Модель:** {analysis['model_name']}
**Дата:** {time.strftime('%Y-%m-%d %H:%M:%S')}

---

{ai_description}

---

*Сгенерировано автоматически.*
"""
    else:
        content = f"""# Техническое описание модели Engee

**Файл:** {zip_file}
**Модель:** {analysis['model_name']}
**Дата:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Ошибка:** {ai_error}

## Статистика
- Всего блоков: {analysis['total_blocks']}
- Подсистем: {len(analysis['subsystems'])}"""

        if analysis['root_blocks']:
            content += "\n\n## Блоки в основной схеме"
            for block in analysis['root_blocks'][:10]:
                content += f"\n- {block['name']} ({block['type']})"

        if analysis['subsystems']:
            content += "\n\n## Подсистемы"
            for subsystem in analysis['subsystems']:
                content += f"\n\n### {subsystem['filename']}"
                content += f"\n- Блоков: {subsystem['block_count']}"
                if subsystem['blocks']:
                    for block in subsystem['blocks'][:5]:
                        content += f"\n- {block['name']} ({block['type']})"

        return content


def _save_md(zip_filename: str, output_dir: str, content: str) -> str:
    base_name = os.path.basename(zip_filename)
    if base_name.lower().endswith('.engee'):
        md_name = base_name[:-6] + '.md'
    elif base_name.lower().endswith('.zip'):
        md_name = base_name[:-4] + '.md'
    else:
        md_name = base_name + '.md'

    output_path = os.path.join(output_dir, md_name)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return output_path


def convert_models(
    input_dir: str,
    output_dir: str,
    api_key: Optional[str] = None,
    on_progress: Optional[Callable[[float], None]] = None,
) -> ConversionResult:
    """
    Конвертирует модели Engee из input_dir в Markdown файлы в output_dir.
    on_progress вызывается на каждый файл (включая пропущенные).
    """
    os.makedirs(output_dir, exist_ok=True)

    if api_key is None:
        api_key = get_api_key()

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY не найден")

    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Папка '{input_dir}' не существует")

    zip_files = sorted([
        f for f in os.listdir(input_dir)
        if f.lower().endswith(('.zip', '.engee'))
    ])
    zip_files_set = set(zip_files)

    processed = set()
    for file in os.listdir(output_dir):
        if file.endswith('.md'):
            base = file[:-3]
            for ext in ('.zip', '.engee'):
                candidate = base + ext
                if candidate in zip_files_set:
                    processed.add(candidate)

    total = len(zip_files)
    skipped = 0
    success = 0
    failed = 0

    for i, zip_file in enumerate(zip_files):
        if zip_file in processed:
            skipped += 1
            if on_progress:
                on_progress(1)
            continue

        full_path = os.path.join(input_dir, zip_file)

        try:
            ok, analysis, _ = _extract_model_data(full_path)
        except Exception:
            failed += 1
            if on_progress:
                on_progress(1)
            continue

        if not ok:
            failed += 1
            if on_progress:
                on_progress(1)
            continue

        model_data = _prepare_data_for_prompt(analysis)
        ai_ok, ai_description, ai_error = _ask_ai(api_key, model_data)
        content = _build_content(zip_file, analysis, ai_ok, ai_description, ai_error)

        try:
            _save_md(zip_file, output_dir, content)
            success += 1
        except Exception:
            failed += 1

        if on_progress:
            on_progress(1)

        # пауза между запросами к API (не нужна после последнего файла)
        if i < len(zip_files) - 1 and zip_file not in processed:
            time.sleep(2)

    return ConversionResult(total=total, success=success, skipped=skipped, failed=failed)
