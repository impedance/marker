# 📊 Отчет: Анализ стилей рисунков в DOCX документах

## 🔍 Обзор анализа

Проведен анализ 6 DOCX документов на предмет наличия и использования стилей `ROSA_Рисунок_Номер` и `ROSA_Рисунок_Текст`.

## 📈 Статистика

| Метрика | Значение |
|---------|----------|
| **Всего документов** | 6 |
| **Документов со стилями рисунков** | 6 (100%) |
| **Документов, использующих стили** | 6 (100%) |
| **Всего подписей рисунков найдено** | 1,666 |

## 📄 Детализация по документам

| Документ | Подписей | Использует стиль |
|----------|----------|------------------|
| `rrm-admin.docx` | 767 | ✅ |
| `РОСА_Менеджер_ресурсов.docx` | 767 | ✅ |
| `cu-admin-install.docx` | 61 | ✅ |
| `РОСА_Центр_Управления_...` | 61 | ✅ |
| `dev-portal-user.docx` | 10 | ✅ |
| `dev-portal-admin.docx` | 0 | ✅ |

## 🎨 Найденные стили

### ✅ Стиль "ROSA_Рисунок_Номер"
**Статус:** Найден во всех документах

**Характеристики:**
- **ID стиля:** `ROSA`, `ROSA5`, `ROSA7`, `ROSAf8` (различаются по документам)
- **Тип:** `paragraph` (параграфный) и `character` (символьный)
- **Выравнивание:** `center` (центрированный)
- **Шрифт:** Roboto
- **Размер:** 24pt (в некоторых документах)

### ❌ Стиль "ROSA_Рисунок_Текст" 
**Статус:** НЕ НАЙДЕН в явном виде

## 🔧 XML Структура стилей

### Определение стиля в `word/styles.xml`:

```xml
<w:style w:type="paragraph" w:styleId="ROSA5">
    <w:name w:val="ROSA_Рисунок_Номер"/>
    <w:pPr>
        <w:jc w:val="center"/>
    </w:pPr>
    <w:rPr>
        <w:rFonts w:ascii="Roboto"/>
        <w:sz w:val="24"/>
    </w:rPr>
</w:style>
```

### Использование в `word/document.xml`:

```xml
<w:p>
    <w:pPr>
        <w:pStyle w:val="ROSA5"/>
    </w:pPr>
    <w:r>
        <w:t>Рисунок 123</w:t>
    </w:r>
</w:p>
```

## 🛠️ Алгоритм извлечения данных

### 1. Поиск стилей в `word/styles.xml`:

```python
def find_figure_styles(styles_xml_content):
    """Находит стили рисунков в styles.xml"""
    root = ET.fromstring(styles_xml_content)
    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    figure_styles = {}
    
    for style in root.findall('.//w:style', namespaces):
        style_id = style.get(f'{{{namespaces["w"]}}}styleId', '')
        name_elem = style.find('.//w:name', namespaces)
        
        if name_elem is not None:
            style_name = name_elem.get(f'{{{namespaces["w"]}}}val', '')
            
            # Поиск стилей рисунков
            if 'ROSA' in style_id and 'рисунок' in style_name.lower():
                figure_styles[style_id] = {
                    'name': style_name,
                    'type': style.get(f'{{{namespaces["w"]}}}type', ''),
                    'formatting': extract_formatting(style, namespaces)
                }
    
    return figure_styles
```

### 2. Извлечение форматирования:

```python
def extract_formatting(style_elem, namespaces):
    """Извлекает параметры форматирования стиля"""
    formatting = {}
    
    # Свойства параграфа
    pPr = style_elem.find('.//w:pPr', namespaces)
    if pPr is not None:
        # Выравнивание
        jc = pPr.find('.//w:jc', namespaces)
        if jc is not None:
            formatting['alignment'] = jc.get(f'{{{namespaces["w"]}}}val', '')
    
    # Свойства текста
    rPr = style_elem.find('.//w:rPr', namespaces)
    if rPr is not None:
        # Размер шрифта
        sz = rPr.find('.//w:sz', namespaces)
        if sz is not None:
            formatting['font_size'] = sz.get(f'{{{namespaces["w"]}}}val', '')
        
        # Шрифт
        rFonts = rPr.find('.//w:rFonts', namespaces)
        if rFonts is not None:
            formatting['font_family'] = rFonts.get(f'{{{namespaces["w"]}}}ascii', '')
    
    return formatting
```

### 3. Поиск использования в `word/document.xml`:

```python
def find_figure_paragraphs(document_xml_content, figure_style_ids):
    """Находит параграфы с подписями рисунков"""
    root = ET.fromstring(document_xml_content)
    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    figure_paragraphs = []
    
    for paragraph in root.findall('.//w:p', namespaces):
        # Проверяем стиль параграфа
        pStyle = paragraph.find('.//w:pStyle', namespaces)
        if pStyle is not None:
            style_val = pStyle.get(f'{{{namespaces["w"]}}}val', '')
            
            if style_val in figure_style_ids:
                # Извлекаем текст
                text_runs = []
                for run in paragraph.findall('.//w:r', namespaces):
                    for t in run.findall('.//w:t', namespaces):
                        if t.text:
                            text_runs.append(t.text)
                
                paragraph_text = ''.join(text_runs).strip()
                
                # Проверяем на наличие рисунков
                drawings = paragraph.findall('.//w:drawing', namespaces)
                
                figure_paragraphs.append({
                    'style': style_val,
                    'text': paragraph_text,
                    'has_drawings': len(drawings) > 0,
                    'drawings_count': len(drawings)
                })
    
    return figure_paragraphs
```

## 📋 Найденные паттерны подписей

**Основной формат:** `Рисунок [число]`

**Примеры:**
- `Рисунок 1`, `Рисунок 2`, ..., `Рисунок 999`
- Специальные ID: `Рисунок 1524204473`, `Рисунок 1577920560`

**Регулярное выражение для извлечения:**
```python
figure_pattern = r'Рисунок\s+(\d+)'
```

## 🎯 Информация, доступная для извлечения

### ✅ Что МОЖНО извлечь:
1. **Номер рисунка** - из текста подписи
2. **Стиль форматирования** - центрирование, шрифт, размер
3. **Связь с изображением** - через элементы `w:drawing`
4. **Позицию в документе** - порядок параграфов

### ⚠️ Что ОТСУТСТВУЕТ:
1. **Отдельный стиль для описания** - нет `ROSA_Рисунок_Текст`
2. **Структурированные метаданные** - только текстовое содержимое
3. **Связь номера с описанием** - нужна дополнительная логика

## 💡 Рекомендации для интеграции

### В `core/adapters/docx_parser.py`:

```python
class DOCXParser:
    def __init__(self):
        self.figure_styles = {}
    
    def parse_styles(self, styles_xml):
        """Парсит стили рисунков из styles.xml"""
        self.figure_styles = self.find_figure_styles(styles_xml)
    
    def parse_paragraph(self, paragraph_elem):
        """Определяет тип параграфа, включая подписи рисунков"""
        style_id = self.get_paragraph_style(paragraph_elem)
        
        if style_id in self.figure_styles:
            text = self.extract_paragraph_text(paragraph_elem)
            figure_match = re.search(r'Рисунок\s+(\d+)', text)
            
            if figure_match:
                return {
                    'type': 'figure_caption',
                    'number': int(figure_match.group(1)),
                    'text': text,
                    'style': self.figure_styles[style_id]
                }
        
        return self.parse_regular_paragraph(paragraph_elem)
```

### В `core/render/markdown_renderer.py`:

```python
def render_figure_caption(self, caption_data):
    """Рендерит подпись рисунка в Markdown"""
    number = caption_data['number']
    text = caption_data['text']
    
    # Центрированная подпись рисунка
    return f"\n<div align=\"center\">\n\n**{text}**\n\n</div>\n\n"
```

## 🚀 Заключение

**Стили рисунков содержат достаточно информации** для автоматической обработки:
- ✅ Надежное определение подписей рисунков
- ✅ Извлечение номеров для создания ссылок  
- ✅ Применение правильного форматирования
- ⚠️ Требуется дополнительная логика для обработки описаний

**Интеграция возможна** с минимальными доработками существующего XML-парсера.

---

**Файлы анализа:**
- `figure_styles_analysis_report.md` - данный отчет
- `figure_analysis_report.json` - подробные данные в JSON формате
- `analyze_figure_styles.py` - скрипт для анализа
- `figure_analysis_summary.py` - оптимизированный анализатор