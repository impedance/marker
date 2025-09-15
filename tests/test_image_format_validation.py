"""Тест проверки, что все ссылки на изображения имеют единый формат ::sign-image."""

import re
from pathlib import Path
from typing import List, Tuple

import pytest


class TestImageFormatValidation:
    """Тест для проверки единого формата ссылок на изображения."""

    def find_markdown_image_links(self, content: str) -> List[str]:
        """Находит обычные markdown ссылки на изображения.
        
        Ищет паттерн: ![alt text](path.png)
        
        Args:
            content (str): Содержимое markdown файла.
            
        Returns:
            List[str]: Список найденных markdown ссылок.
        """
        pattern = r'!\[([^\]]*)\]\(([^)]*\.png)\)'
        matches = re.findall(pattern, content)
        return [f"![{alt}]({path})" for alt, path in matches]

    def find_sign_image_blocks(self, content: str) -> List[str]:
        """Находит блоки ::sign-image.
        
        Args:
            content (str): Содержимое markdown файла.
            
        Returns:
            List[str]: Список найденных src путей из sign-image блоков.
        """
        pattern = r'::sign-image\s*---\s*src:\s*([^\n]+)\s*sign:.*?---\s*::'
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        return [src.strip() for src in matches]

    def check_file_image_format(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """Проверяет формат ссылок на изображения в одном файле.
        
        Args:
            file_path (Path): Путь к markdown файлу.
            
        Returns:
            Tuple[List[str], List[str]]: (markdown_links, sign_image_links)
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            markdown_links = self.find_markdown_image_links(content)
            sign_image_links = self.find_sign_image_blocks(content)
            return markdown_links, sign_image_links
        except Exception as e:
            print(f"Ошибка чтения файла {file_path}: {e}")
            return [], []

    def test_all_image_links_are_sign_image_format(self):
        """Основной тест: все ссылки на изображения должны быть в формате ::sign-image."""
        output_dir = Path("test-fixed-output")
        
        if not output_dir.exists():
            pytest.skip("Выходная директория 'output' не найдена")
        
        # Найти все .md файлы
        md_files = list(output_dir.glob("**/*.md"))
        
        files_with_markdown_links = []
        total_markdown_links = 0
        total_sign_image_links = 0
        
        for md_file in md_files:
            markdown_links, sign_image_links = self.check_file_image_format(md_file)
            
            if markdown_links:
                files_with_markdown_links.append((md_file, markdown_links))
                total_markdown_links += len(markdown_links)
            
            total_sign_image_links += len(sign_image_links)
        
        # Выводим результаты
        print(f"\n=== АНАЛИЗ ФОРМАТОВ ССЫЛОК НА ИЗОБРАЖЕНИЯ ===")
        print(f"Всего ::sign-image блоков: {total_sign_image_links}")
        print(f"Неправильных markdown ссылок: {total_markdown_links}")
        
        if files_with_markdown_links:
            print(f"\n❌ НАЙДЕНЫ ФАЙЛЫ С НЕПРАВИЛЬНЫМИ ССЫЛКАМИ:")
            for file_path, links in files_with_markdown_links[:5]:  # Показываем первые 5
                relative_path = file_path.relative_to(output_dir)
                print(f"  📄 {relative_path}")
                for link in links[:3]:  # Показываем первые 3 ссылки
                    print(f"    - {link}")
                if len(links) > 3:
                    print(f"    ... и еще {len(links) - 3} ссылок")
            
            if len(files_with_markdown_links) > 5:
                print(f"  ... и еще {len(files_with_markdown_links) - 5} файлов")
        else:
            print("✅ ВСЕ ССЫЛКИ В ПРАВИЛЬНОМ ФОРМАТЕ!")
        
        # Основная проверка
        assert total_markdown_links == 0, (
            f"Найдено {total_markdown_links} ссылок в неправильном markdown формате "
            f"в {len(files_with_markdown_links)} файлах. "
            f"Все ссылки должны быть в формате ::sign-image"
        )

    def test_sign_image_format_structure(self):
        """Тест проверки правильности структуры ::sign-image блоков."""
        test_content = """
        Правильный блок:
        ::sign-image
        ---
        src: /images/developer/user/picture_1.png
        sign: Рисунок 1 – Описание
        ---
        ::
        
        Неправильная ссылка:
        ![Image image123](path/to/image.png)
        """
        
        markdown_links = self.find_markdown_image_links(test_content)
        sign_image_links = self.find_sign_image_blocks(test_content)
        
        assert len(markdown_links) == 1, f"Должна быть найдена 1 markdown ссылка, найдено: {len(markdown_links)}"
        assert len(sign_image_links) == 1, f"Должен быть найден 1 sign-image блок, найдено: {len(sign_image_links)}"
        assert sign_image_links[0] == "/images/developer/user/picture_1.png", f"Неправильный путь: {sign_image_links[0]}"

    def test_expected_sign_image_path_format(self):
        """Тест проверки ожидаемого формата путей в sign-image блоках."""
        output_dir = Path("output")
        
        if not output_dir.exists():
            pytest.skip("Выходная директория 'output' не найдена")
        
        # Проверяем несколько файлов на предмет правильного формата путей
        md_files = list(output_dir.glob("**/*.md"))[:5]  # Берем первые 5 файлов
        
        correct_path_pattern = r'^/images/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+\.png$'
        
        for md_file in md_files:
            _, sign_image_links = self.check_file_image_format(md_file)
            
            for src_path in sign_image_links:
                # Пока что просто проверяем, что это путь к PNG
                assert src_path.endswith('.png'), f"Путь должен заканчиваться на .png: {src_path}"
                
                # Здесь можно добавить более строгие проверки формата пути
                # когда будет реализован правильный формат
                if src_path.startswith('/images/'):
                    # Если путь уже в правильном формате, проверяем его структуру
                    assert re.match(correct_path_pattern, src_path), (
                        f"Путь не соответствует ожидаемому формату: {src_path}"
                    )