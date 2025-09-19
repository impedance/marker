# Задача: Исправление отображения изображений в таблицах

## Исходная проблема
В главе "Просмотр и редактирование панели" документа `@docs-work/rukovod_adminis_31eks-_monit-2.3.0.docx` есть таблица с изображениями, которая неправильно формируется в markdown. Проблема наблюдается в первой таблице в файле `@out-test/rukovodadminis31eks-monit-2.3.0/030000.veb-interfeis/030200.razdely-veb-interfeisa.md` сразу после текста "Возможности просмотра панелей".

## Ожидаемый результат
Согласно скриншоту `@docs-work/Screenshot from 2025-09-19 12-14-47.png`, изображения должны корректно размещаться в ячейках таблицы как элементы интерфейса (кнопки, иконки) с соответствующими описаниями действий.

## Проведенный анализ

### Первоначальная проблема
Изображения в таблицах отображались как отдельные блоки `::sign-image`, что разрывало структуру markdown таблиц:

```markdown
| Действие | Описание |
| --- | --- |
| ::sign-image
---
src: /image43.png
sign: Image image43
---
:: | Переключиться в режим редактирования панели. |
```

### Диагностика через отладку
Создали скрипт `debug_table_images.py`, который показал:
- Изображения в таблицах находятся в параграфах со стилем `ROSA_Таблица_Текст`
- Рядом с таблицами НЕТ параграфов со стилем `ROSA_Рисунок_Номер`
- Изображения имеют осмысленные имена: "Рисунок 64", "Рисунок 65", "Рисунок 181" и т.д.
- Для изображений в таблицах подписи не извлекаются из стиля `ROSA_Рисунок_Номер` (это корректно)

## Реализованное решение

### 1. Изменения в `core/render/markdown_renderer.py`
Добавили специальную обработку изображений в функции `_render_block_for_table()`:

```python
if type == "image":
    # For images in table cells, use inline markdown format instead of block format
    path = asset_map.get(block.resource_id, "about:blank")
    sign_text = block.caption if block.caption else (block.alt if block.alt else f"Рисунок {block.resource_id}")
    # Use standard markdown image syntax for table cells
    escaped_sign = _escape_table_content(sign_text)
    return f"![{escaped_sign}](/{block.resource_id}.png)"
```

### 2. Улучшения в `core/adapters/docx_parser.py`
Улучшили alt-текст изображений, используя имена из docx:

```python
# Create Image block with better alt text using image name
alt_text = image_name if image_name else f"Image {resource_ref.id}"
image = Image(
    alt=alt_text,
    resource_id=resource_ref.id,
    caption=caption
)
```

### 3. Тесты
Создали `tests/test_table_image_rendering.py` с тестами для:
- Изображений в ячейках таблиц
- Множественных изображений в таблице
- Эскейпинга специальных символов в подписях

## Текущий результат
Таблицы теперь отображаются корректно:

```markdown
| Действие | Описание |
| --- | --- |
| ![Рисунок 64](/image43.png) | Переключиться в режим редактирования панели. ![Рисунок 181](/image44.png) Режим редактирования также открывается при создании новой панели и при нажатии на пиктограмму редактирования виджета. |
| ![Рисунок 65](/image45.png) | Открыть меню действий (ниже описание действий). |
```

## ВАЖНАЯ НЕРЕШЕННАЯ ЗАДАЧА

### Проблема единообразия формата
В проекте используется специальный формат для изображений:

```markdown
::sign-image
---
src: /image001.png
sign: Подпись к рисунку
---
::
```

Текущее решение нарушает единообразие:
- **Обычные изображения** (вне таблиц): используют формат `::sign-image`
- **Изображения в таблицах**: используют стандартный markdown `![alt](src)`

### Требуется решение
Нужно адаптировать формат `::sign-image` для корректной работы в таблицах, сохранив единообразие проекта. Возможные варианты:

1. **Компактный однострочный формат:**
   ```
   | ::sign-image{src: /image43.png, sign: Рисунок 64}:: | Описание |
   ```

2. **HTML-подобный формат:**
   ```
   | <sign-image src="/image43.png" sign="Рисунок 64"/> | Описание |
   ```

3. **Специальный маркер:**
   ```
   | :::sign-image src="/image43.png" sign="Рисунок 64"::: | Описание |
   ```

## Файлы для продолжения работы
- `core/render/markdown_renderer.py` - функция `_render_block_for_table()`
- `tests/test_table_image_rendering.py` - тесты для проверки
- Тестовый документ: `docs-work/rukovod_adminis_31eks-_monit-2.3.0.docx`
- Пример результата: `output/test-table-fix2/rukovodadminis31eks-monit-2.3.0/030000.veb-interfeis/030200.razdely-veb-interfeisa.md`

## Контекст предыдущих изменений
Перед этой задачей была выполнена работа по изменению извлечения подписей изображений - теперь подписи берутся напрямую из стиля `ROSA_Рисунок_Номер` вместо сложной логики комбинирования источников.

## Команды для тестирования
```bash
# Генерация тестового вывода
source .venv/bin/activate && python doc2chapmd.py build docs-work/rukovod_adminis_31eks-_monit-2.3.0.docx -o output/test-table

# Запуск тестов
source .venv/bin/activate && python -m pytest tests/test_table_image_rendering.py -v
```

## Статус
- ✅ Таблицы больше не ломаются изображениями
- ✅ Alt-текст изображений улучшен
- ✅ Тесты написаны и проходят
- ❌ **Нужно решить проблему единообразия формата `::sign-image`**