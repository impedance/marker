#!/usr/bin/env python3
"""
Анализ стилей для рисунков в DOCX документах.
Ищет стили ROSA_Рисунок_Номер и ROSA_Рисунок_Текст и анализирует их использование.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class FigureStyleAnalyzer:
    """Анализатор стилей рисунков в DOCX документах."""
    
    def __init__(self):
        self.target_styles = [
            "ROSA_Рисунок_Номер",
            "ROSA_Рисунок_Текст",
            "Рисунок",
            "Figure"
        ]
        
    def analyze_docx(self, docx_path: Path) -> Dict:
        """Анализирует один DOCX файл на наличие стилей рисунков."""
        try:
            with zipfile.ZipFile(docx_path, 'r') as docx_zip:
                # Получаем список файлов в архиве
                file_list = docx_zip.namelist()
                
                result = {
                    'file': str(docx_path.name),
                    'styles_found': [],
                    'paragraphs_with_figure_styles': [],
                    'errors': []
                }
                
                # Анализ стилей
                if 'word/styles.xml' in file_list:
                    result.update(self._analyze_styles_xml(docx_zip))
                
                # Анализ документа
                if 'word/document.xml' in file_list:
                    result.update(self._analyze_document_xml(docx_zip))
                    
                return result
                
        except Exception as e:
            return {
                'file': str(docx_path.name),
                'error': f'Ошибка при анализе: {str(e)}'
            }
    
    def _analyze_styles_xml(self, docx_zip: zipfile.ZipFile) -> Dict:
        """Анализирует word/styles.xml для поиска стилей рисунков."""
        try:
            styles_xml = docx_zip.read('word/styles.xml')
            root = ET.fromstring(styles_xml)
            
            # Пространства имен Word
            namespaces = {
                'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
            }
            
            styles_found = []
            
            for style in root.findall('.//w:style', namespaces):
                style_id = style.get(f'{{{namespaces["w"]}}}styleId', '')
                style_type = style.get(f'{{{namespaces["w"]}}}type', '')
                
                # Получаем название стиля
                name_elem = style.find('.//w:name', namespaces)
                style_name = name_elem.get(f'{{{namespaces["w"]}}}val', '') if name_elem is not None else ''
                
                # Проверяем, соответствует ли стиль нашим целевым
                is_target_style = (
                    any(target in style_id for target in self.target_styles) or
                    any(target in style_name for target in self.target_styles) or
                    'рисунок' in style_id.lower() or
                    'рисунок' in style_name.lower() or
                    'figure' in style_id.lower() or
                    'figure' in style_name.lower()
                )
                
                if is_target_style:
                    style_info = {
                        'styleId': style_id,
                        'styleName': style_name,
                        'type': style_type
                    }
                    
                    # Дополнительная информация о стиле
                    basedOn = style.find('.//w:basedOn', namespaces)
                    if basedOn is not None:
                        style_info['basedOn'] = basedOn.get(f'{{{namespaces["w"]}}}val', '')
                    
                    # Получаем свойства форматирования
                    formatting = self._extract_style_formatting(style, namespaces)
                    if formatting:
                        style_info['formatting'] = formatting
                    
                    styles_found.append(style_info)
            
            return {'styles_found': styles_found}
            
        except Exception as e:
            return {'styles_error': f'Ошибка анализа styles.xml: {str(e)}'}
    
    def _analyze_document_xml(self, docx_zip: zipfile.ZipFile) -> Dict:
        """Анализирует word/document.xml для поиска использования стилей рисунков."""
        try:
            doc_xml = docx_zip.read('word/document.xml')
            root = ET.fromstring(doc_xml)
            
            namespaces = {
                'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
            }
            
            paragraphs_with_figure_styles = []
            
            for paragraph in root.findall('.//w:p', namespaces):
                # Проверяем стиль параграфа
                pStyle = paragraph.find('.//w:pStyle', namespaces)
                if pStyle is not None:
                    style_val = pStyle.get(f'{{{namespaces["w"]}}}val', '')
                    
                    is_figure_style = (
                        any(target in style_val for target in self.target_styles) or
                        'рисунок' in style_val.lower() or
                        'figure' in style_val.lower()
                    )
                    
                    if is_figure_style:
                        # Получаем текст параграфа
                        text_runs = []
                        for run in paragraph.findall('.//w:r', namespaces):
                            for t in run.findall('.//w:t', namespaces):
                                if t.text:
                                    text_runs.append(t.text)
                        
                        paragraph_text = ''.join(text_runs)
                        
                        # Проверяем на наличие рисунков
                        drawings = paragraph.findall('.//w:drawing', namespaces)
                        
                        paragraph_info = {
                            'style': style_val,
                            'text': paragraph_text.strip(),
                            'has_drawings': len(drawings) > 0,
                            'drawings_count': len(drawings)
                        }
                        
                        # Анализируем содержимое рисунков если есть
                        if drawings:
                            drawing_info = self._analyze_drawings(drawings, namespaces)
                            paragraph_info['drawing_details'] = drawing_info
                        
                        paragraphs_with_figure_styles.append(paragraph_info)
            
            return {'paragraphs_with_figure_styles': paragraphs_with_figure_styles}
            
        except Exception as e:
            return {'document_error': f'Ошибка анализа document.xml: {str(e)}'}
    
    def _extract_style_formatting(self, style_elem, namespaces: Dict[str, str]) -> Dict:
        """Извлекает информацию о форматировании из стиля."""
        formatting = {}
        
        # Свойства параграфа
        pPr = style_elem.find('.//w:pPr', namespaces)
        if pPr is not None:
            # Выравнивание
            jc = pPr.find('.//w:jc', namespaces)
            if jc is not None:
                formatting['alignment'] = jc.get(f'{{{namespaces["w"]}}}val', '')
            
            # Отступы
            ind = pPr.find('.//w:ind', namespaces)
            if ind is not None:
                for attr in ['left', 'right', 'firstLine', 'hanging']:
                    val = ind.get(f'{{{namespaces["w"]}}}{attr}', '')
                    if val:
                        formatting[f'indent_{attr}'] = val
        
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
    
    def _analyze_drawings(self, drawings, namespaces: Dict[str, str]) -> List[Dict]:
        """Анализирует элементы рисунков."""
        drawing_details = []
        
        for drawing in drawings:
            detail = {}
            
            # Попытка найти описание рисунка
            # (в реальных документах структура может быть сложнее)
            try:
                # Ищем различные элементы, которые могут содержать информацию о рисунке
                for elem in drawing.iter():
                    if elem.text and elem.text.strip():
                        if 'description' not in detail:
                            detail['description'] = []
                        detail['description'].append(elem.text.strip())
            except:
                pass
            
            drawing_details.append(detail)
        
        return drawing_details
    
    def analyze_all_documents(self, docs_dir: Path) -> Dict:
        """Анализирует все DOCX документы в директории."""
        docx_files = list(docs_dir.glob('*.docx'))
        # Исключаем временные файлы Word
        docx_files = [f for f in docx_files if not f.name.startswith('~$')]
        
        results = {}
        
        for docx_file in docx_files:
            print(f"Анализируем: {docx_file.name}")
            results[docx_file.name] = self.analyze_docx(docx_file)
        
        return results


def search_all_figure_related_content(docs_dir: Path):
    """Дополнительный поиск всего контента связанного с рисунками."""
    print("\n=== ДОПОЛНИТЕЛЬНЫЙ ПОИСК ВСЕГО СОДЕРЖИМОГО СВЯЗАННОГО С РИСУНКАМИ ===\n")
    
    docx_files = list(docs_dir.glob('*.docx'))
    docx_files = [f for f in docx_files if not f.name.startswith('~$')]
    
    for docx_file in docx_files:
        try:
            with zipfile.ZipFile(docx_file, 'r') as docx_zip:
                print(f"\n📄 {docx_file.name}:")
                
                # Ищем во всех XML файлах
                for xml_file in docx_zip.namelist():
                    if xml_file.endswith('.xml'):
                        try:
                            content = docx_zip.read(xml_file).decode('utf-8')
                            
                            # Ищем различные паттерны связанные с рисунками
                            patterns = [
                                r'ROSA.*[Рр]исунок',
                                r'[Рр]исунок.*ROSA',
                                r'ROSA.*[Ff]igure',
                                r'[Ff]igure.*ROSA',
                                r'рисунок.*номер',
                                r'рисунок.*текст',
                                r'figure.*number',
                                r'figure.*text'
                            ]
                            
                            found_patterns = []
                            for pattern in patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                if matches:
                                    found_patterns.extend(matches)
                            
                            if found_patterns:
                                print(f"  🔍 {xml_file}: найдены паттерны {set(found_patterns)}")
                        
                        except Exception as e:
                            pass  # Пропускаем файлы с ошибками декодирования
                            
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")


def main():
    """Основная функция анализа."""
    analyzer = FigureStyleAnalyzer()
    docs_dir = Path('/home/spec/work/rosa/marker/real-docs')
    
    print("=== АНАЛИЗ СТИЛЕЙ РИСУНКОВ В DOCX ДОКУМЕНТАХ ===\n")
    
    results = analyzer.analyze_all_documents(docs_dir)
    
    # Дополнительный поиск
    search_all_figure_related_content(docs_dir)
    
    # Выводим результаты
    for filename, result in results.items():
        print(f"\n📄 ДОКУМЕНТ: {filename}")
        print("=" * 50)
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
            continue
        
        # Найденные стили
        if result.get('styles_found'):
            print("\n🎨 НАЙДЕННЫЕ СТИЛИ:")
            for style in result['styles_found']:
                print(f"  • ID: {style.get('styleId', 'N/A')}")
                print(f"    Название: {style.get('styleName', 'N/A')}")
                print(f"    Тип: {style.get('type', 'N/A')}")
                if 'basedOn' in style:
                    print(f"    Основан на: {style['basedOn']}")
                if 'formatting' in style:
                    print(f"    Форматирование: {style['formatting']}")
                print()
        else:
            print("🔍 Целевые стили не найдены в styles.xml")
        
        # Параграфы с стилями рисунков
        if result.get('paragraphs_with_figure_styles'):
            print("\n📝 ПАРАГРАФЫ СО СТИЛЯМИ РИСУНКОВ:")
            for para in result['paragraphs_with_figure_styles']:
                print(f"  • Стиль: {para['style']}")
                print(f"    Текст: {para['text'][:100]}{'...' if len(para['text']) > 100 else ''}")
                print(f"    Рисунков: {para['drawings_count']}")
                if para.get('drawing_details'):
                    print(f"    Детали рисунков: {para['drawing_details']}")
                print()
        else:
            print("📝 Параграфы со стилями рисунков не найдены")
        
        if result.get('styles_error'):
            print(f"⚠️  Ошибка анализа стилей: {result['styles_error']}")
        
        if result.get('document_error'):
            print(f"⚠️  Ошибка анализа документа: {result['document_error']}")


if __name__ == '__main__':
    main()