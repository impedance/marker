#!/usr/bin/env python3
"""
Краткий анализ данных о рисунках в DOCX документах.
Фокус на главных выводах без подробного вывода.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import json


def analyze_figure_data():
    """Анализирует данные о рисунках в DOCX документах."""
    docs_dir = Path('/home/spec/work/rosa/marker/real-docs')
    docx_files = [f for f in docs_dir.glob('*.docx') if not f.name.startswith('~$')]
    
    report = {
        'total_documents': len(docx_files),
        'documents_with_rosa_figure_styles': [],
        'figure_caption_patterns': set(),
        'figure_numbering_found': False,
        'recommendations': []
    }
    
    # Паттерны для поиска подписей рисунков
    figure_patterns = [
        r'[Рр]исунок\s+\d+',
        r'Figure\s+\d+',
        r'[Рр]исунок\s+[IVXLCDM]+',  # Римские числа
        r'[Рр]ис\.\s*\d+',
        r'Fig\.\s*\d+'
    ]
    
    for docx_file in docx_files:
        doc_info = {
            'name': docx_file.name,
            'has_rosa_figure_style': False,
            'figure_captions_count': 0,
            'uses_figure_style': False
        }
        
        try:
            with zipfile.ZipFile(docx_file, 'r') as docx_zip:
                # Проверяем стили
                if 'word/styles.xml' in docx_zip.namelist():
                    styles_xml = docx_zip.read('word/styles.xml').decode('utf-8')
                    if 'ROSA' in styles_xml and ('Рисунок' in styles_xml or 'рисунок' in styles_xml):
                        doc_info['has_rosa_figure_style'] = True
                
                # Анализируем document.xml
                if 'word/document.xml' in docx_zip.namelist():
                    doc_xml = docx_zip.read('word/document.xml').decode('utf-8')
                    
                    # Подсчитываем подписи рисунков
                    for pattern in figure_patterns:
                        matches = re.findall(pattern, doc_xml)
                        doc_info['figure_captions_count'] += len(matches)
                        for match in matches:
                            report['figure_caption_patterns'].add(match[:20])  # Ограничиваем длину
                    
                    # Проверяем использование стилей рисунков
                    if 'pStyle w:val="ROSA' in doc_xml and 'рисунок' in doc_xml.lower():
                        doc_info['uses_figure_style'] = True
                        
        except Exception as e:
            doc_info['error'] = str(e)
        
        if doc_info['has_rosa_figure_style']:
            report['documents_with_rosa_figure_styles'].append(doc_info)
    
    # Преобразуем set в list для JSON
    report['figure_caption_patterns'] = list(report['figure_caption_patterns'])
    
    # Подсчет статистики
    total_captions = sum(doc.get('figure_captions_count', 0) for doc in report['documents_with_rosa_figure_styles'])
    docs_with_styles = len(report['documents_with_rosa_figure_styles'])
    docs_using_styles = sum(1 for doc in report['documents_with_rosa_figure_styles'] if doc.get('uses_figure_style'))
    
    report['summary'] = {
        'documents_with_rosa_styles': docs_with_styles,
        'documents_actually_using_styles': docs_using_styles,
        'total_figure_captions_found': total_captions,
        'figure_numbering_detected': total_captions > 0
    }
    
    # Генерируем рекомендации
    if docs_with_styles > 0:
        report['recommendations'].append("✅ Найдены стили ROSA_Рисунок_Номер в документах")
    else:
        report['recommendations'].append("❌ Стили рисунков не найдены")
    
    if total_captions > 0:
        report['recommendations'].append(f"✅ Найдено {total_captions} подписей рисунков")
        report['recommendations'].append("✅ Возможна автоматическая обработка подписей рисунков")
    else:
        report['recommendations'].append("❌ Подписи рисунков не найдены в явном виде")
    
    if docs_using_styles == 0:
        report['recommendations'].append("⚠️ Стили определены, но фактически не используются")
        report['recommendations'].append("💡 Рекомендуется изучить альтернативные способы разметки рисунков")
    
    return report


def main():
    """Основная функция."""
    print("🔍 Анализ данных рисунков в DOCX документах...\n")
    
    report = analyze_figure_data()
    
    # Сохраняем отчет в JSON
    with open('/home/spec/work/rosa/marker/figure_analysis_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # Выводим краткий отчет
    print("=== КРАТКИЙ ОТЧЕТ О ДАННЫХ РИСУНКОВ ===")
    print(f"📊 Всего документов проанализировано: {report['total_documents']}")
    print(f"🎨 Документов с стилями ROSA для рисунков: {report['summary']['documents_with_rosa_styles']}")
    print(f"📝 Документов, использующих стили рисунков: {report['summary']['documents_actually_using_styles']}")
    print(f"🖼️ Всего найдено подписей рисунков: {report['summary']['total_figure_captions_found']}")
    
    print("\n=== НАЙДЕННЫЕ ДОКУМЕНТЫ С СТИЛЯМИ РИСУНКОВ ===")
    for doc in report['documents_with_rosa_figure_styles']:
        status = "✅ используется" if doc.get('uses_figure_style') else "⚠️ не используется"
        print(f"• {doc['name']}: {doc['figure_captions_count']} подписей, стиль {status}")
    
    if report['figure_caption_patterns']:
        print("\n=== НАЙДЕННЫЕ ПАТТЕРНЫ ПОДПИСЕЙ РИСУНКОВ ===")
        for pattern in sorted(report['figure_caption_patterns']):
            print(f"• {pattern}")
    
    print("\n=== РЕКОМЕНДАЦИИ ===")
    for rec in report['recommendations']:
        print(rec)
    
    print(f"\n📄 Подробный отчет сохранен в: figure_analysis_report.json")


if __name__ == '__main__':
    main()