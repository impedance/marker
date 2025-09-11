
# Новый модуль: `core/output/hierarchical_writer.py`

```python
# core/output/hierarchical_writer.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import re
from typing import List, Tuple, Optional

# Используем уже существующие части пайплайна
from core.adapters.document_parser import parse_document
from core.split.chapter_splitter import ChapterRules  # опционально, если хочешь выделять "нулевую" главу
from core.render.markdown_renderer import render_markdown
from core.output.writer import Writer

# ============ ВСПОМОГАТЕЛЬНЫЕ ============

_HEADING_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)$')   # "1.2.3 Заголовок"
_HEADING_RE_DOT = re.compile(r'^(\d+(?:\.\d+)*)\.\s+(.+)$')  # "1.2.3. Заголовок"
_HEADING_RE_DASH = re.compile(r'^(\d+(?:\.\d+)*)\s*[-–—]\s*(.+)$')  # "1.2.3 - Заголовок"

def _split_number_and_title(text: str) -> Tuple[List[int], str]:
    """
    Возвращает ([1,2,3], "Заголовок") для "1.2.3 Заголовок".
    Если номера нет — ([ ], исходный_текст).
    """
    s = text.strip()
    for rx in (_HEADING_RE, _HEADING_RE_DOT, _HEADING_RE_DASH):
        m = rx.match(s)
        if m:
            nums = [int(x) for x in m.group(1).split(".")]
            return nums, m.group(2).strip()
    return [], s

def _clean_filename(title: str) -> str:
    # Сохранить кириллицу, убрать служебные символы ФС
    bad = r'[/\\:*?"<>|]'
    title = re.sub(bad, " ", title).strip()
    # сжать пробелы
    title = re.sub(r"\s{2,}", " ", title)
    return title

def _code_for_levels(nums: List[int]) -> str:
    """
    Сформировать 6-значный (или 4/2-значный) код из уровней:
    [1]     -> "010000"
    [1,2]   -> "010200"
    [1,2,3] -> "010203"
    Правило: по 2 цифры на уровень. Отсутствующие уровни = "00".
    """
    a = f"{(nums[0] if len(nums) >= 1 else 0):02d}"
    b = f"{(nums[1] if len(nums) >= 2 else 0):02d}"
    c = f"{(nums[2] if len(nums) >= 3 else 0):02d}"
    return f"{a}{b}{c}"

@dataclass
class _Section:
    level: int
    number: List[int]            # [1], [1,2], [1,2,3]
    title: str                   # Заголовок без номера
    blocks: list                 # Подмножество blocks InternalDoc для рендера

# ============ ОСНОВА ============

def _collect_sections(blocks: list) -> List[_Section]:
    """
    Разбивает единый InternalDoc.blocks на секции для записи:
    - index.md для H1 (контент до первого H2);
    - отдельные файлы для H2 (как 010100.*), причём вводный текст H2 до первого H3 идёт в 010100.*,
      а каждый H3 — отдельный файл 010101.*, 010102.*, ...
    Глубже H3 оставляем внутри соответствующего H3-файла.
    """
    sections: List[_Section] = []

    cur_h1: Optional[_Section] = None
    cur_h2_intro: Optional[_Section] = None
    cur_h3: Optional[_Section] = None

    def flush_h3():
        nonlocal cur_h3
        if cur_h3 and cur_h3.blocks:
            sections.append(cur_h3)
        cur_h3 = None

    def flush_h2():
        nonlocal cur_h2_intro
        # Вводный файл для H2 (…00) пишем только если в нём есть контент
        if cur_h2_intro and cur_h2_intro.blocks:
            sections.append(cur_h2_intro)
        cur_h2_intro = None

    def flush_h1():
        nonlocal cur_h1
        if cur_h1 and cur_h1.blocks:
            sections.append(cur_h1)  # index.md для главы
        cur_h1 = None

    # Пройдём по блокам
    for blk in blocks:
        if getattr(blk, "type", None) == "heading":
            text: str = blk.text or ""
            lvl: int = blk.level
            nums, ttl = _split_number_and_title(text)

            # интересуют только уровни 1..3 для разбиения
            if lvl == 1 and nums:
                # новая глава → завершить предыдущие
                flush_h3()
                flush_h2()
                flush_h1()
                cur_h1 = _Section(level=1, number=[nums[0]], title=ttl, blocks=[blk])
                # index.md заполняем дальше — абзацы до первого H2
                continue

            if lvl == 2 and nums and cur_h1:
                # новый раздел второго уровня
                flush_h3()
                flush_h2()
                cur_h2_intro = _Section(level=2, number=[nums[0], nums[1]], title=ttl, blocks=[blk])
                continue

            if lvl == 3 and nums and cur_h1 and cur_h2_intro:
                # новый подраздел третьего уровня
                flush_h3()
                cur_h3 = _Section(level=3, number=[nums[0], nums[1], nums[2]], title=ttl, blocks=[blk])
                continue

            # другие заголовки (уровни >3) — просто отправим куда сейчас пишем
            # (внутрь cur_h3, либо cur_h2_intro, либо cur_h1)
            target = cur_h3 or cur_h2_intro or cur_h1
            if target:
                target.blocks.append(blk)
            continue

        # не- заголовок → попадёт в текущую «открытую» секцию
        target = cur_h3 or cur_h2_intro or cur_h1
        if target:
            target.blocks.append(blk)

    # финальный сброс
    flush_h3()
    flush_h2()
    flush_h1()
    return sections


def export_docx_hierarchy(docx_path: str | os.PathLike, out_root: str | os.PathLike) -> List[Path]:
    """
    Главная функция. Разбирает .docx → InternalDoc,
    режет на секции (см. правила выше) и пишет:
      - для каждого H1: <AA0000>.<Название>/index.md + images/
      - для каждого H2: файлы <AABB00>.<Название>.md
      - для каждого H3: файлы <AABBCC>.<Название>.md
    Возвращает список созданных файлов.
    """
    writer = Writer()
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # 1) получаем InternalDoc (включая уровни и текст заголовков с номерами)
    doc, _resources = parse_document(str(docx_path))  # ресурсы картинок можно вынести отдельно по желанию

    # 2) режем на секции в оперативке
    sections = _collect_sections(doc.blocks)

    written: List[Path] = []
    h1_dir: Optional[Path] = None
    last_h1_num: Optional[int] = None

    for sec in sections:
        code = _code_for_levels(sec.number)
        safe_title = _clean_filename(sec.title)

        if sec.level == 1:
            # Папка главы: 010000.Название
            last_h1_num = sec.number[0]
            h1_dir = out_root / f"{code}.{safe_title}"
            writer.ensure_dir(h1_dir)
            writer.ensure_dir(h1_dir / "images")

            # index.md
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            path = h1_dir / "index.md"
            writer.write_text(path, md)
            written.append(path)

        elif sec.level == 2:
            assert h1_dir is not None and last_h1_num == sec.number[0], \
                "Внутренний порядок H2 нарушен: нет родительской H1"
            # Файл уровня 2: 010200.Название.md
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            path = h1_dir / f"{code}.{safe_title}.md"
            writer.write_text(path, md)
            written.append(path)

        elif sec.level == 3:
            assert h1_dir is not None and last_h1_num == sec.number[0], \
                "Внутренний порядок H3 нарушен: нет родительской H1"
            # Файл уровня 3: 010203.Название.md
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            path = h1_dir / f"{code}.{safe_title}.md"
            writer.write_text(path, md)
            written.append(path)

        else:
            # На всякий случай — всё, что выше H3, складываем в текущий контейнер секции
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            # если вдруг проскочит >3, поднимем до ближайшего известного кода
            fallback_code = _code_for_levels(sec.number[:3])
            path = h1_dir / f"{fallback_code}.{safe_title}.md" if h1_dir else (out_root / f"{fallback_code}.{safe_title}.md")
            writer.write_text(path, md)
            written.append(path)

    return written
```

---

## Как встроить

1. Помести файл выше в проект по пути:
   `core/output/hierarchical_writer.py`

2. В CLI/скрипте конвертации добавь команду (пример):

```python
# doc2chapmd.py (пример)
import typer
from core.output.hierarchical_writer import export_docx_hierarchy

app = typer.Typer(help="DOCX → иерархия глав")

@app.command()
def build(
    docx: str = typer.Argument(..., help="Путь к .docx"),
    out: str = typer.Option("out", help="Каталог вывода"),
):
    written = export_docx_hierarchy(docx, out)
    for p in written:
        print("✓", p)

if __name__ == "__main__":
    app()
```

3. Запуск:

```bash
python doc2chapmd.py build /path/to/dev-portal-admin.docx --out ./output
```

В результате получишь дерево вида:

```
output/
└── dev-portal-admin/
    ├── 010000.Общие положения/
    │   ├── index.md
    │   └── images/
    ├── 020000.Архитектура системы/
    │   ├── index.md
    │   ├── 020100.Архитектурные решения системы.md
    │   └── images/
    ├── 030000.Требования/
    │   ├── index.md
    │   ├── 030100.Требования к ПО.md
    │   ├── 030200.Требования к оборудованию.md
    │   └── images/
    ├── 040000.Установка и запуск/
    │   ├── index.md
    │   ├── 040100.Подготовка окружения.md
    │   ├── 040101.Установка Docker.md
    │   ├── 040102.Развёртывание Traefik.md
    │   ├── 040200.Установка Комплекса.md
    │   ├── 040300.Запуск Комплекса.md
    │   └── images/
    ├── 050000.Тонкая настройка ОС/
    │   ├── index.md
    │   ├── 050100.Настройки производительности.md
    │   └── images/
    └── 060000.Мониторинг и диагностика/
        ├── index.md
        ├── 060100.Расположение ПО и логов.md
        └── images/
```

— где H2 сохраняются как `AABB00.*.md`, а H3 — как `AABBCC.*.md`.
Если у H2 есть «вступительный» текст до первого H3 — он попадёт в `AABB00.*.md`. Каждый H3 — отдельный файл (`…01`, `…02`, и т.д.), как на картинке из ТЗ.

---

## Примечания и расширения

* Модуль предполагает, что **`docx_parser` уже добавляет номера** в текст заголовков (например: `"# 2 Архитектура системы"` и `"## 2.1 Архитектурные решения системы"`). В твоём проекте это уже реализовано (см. `core/adapters/docx_parser.py` + `core/numbering/heading_numbering.py`).
* Папка `images/` создаётся внутри каждой H1-главы. Перенос реальных изображений можно добавить через ваш `assets_exporter` — если потребуется, допишу хелпер, чтобы маппить ресурсы в соответствующую `images` директорию конкретной главы.
* Если нужно учитывать «нулевую» главу (Аннотация/Содержание), можно предварительно прогнать документ через `ChapterRules` и отделить front-matter. Сейчас экспорт идёт «как есть», и нумерация берётся из заголовков.

Хочешь — сразу сделаю версию, которая подтянет экспорт изображений в `images/` каждой главы и поправит относительные ссылки внутри Markdown?
