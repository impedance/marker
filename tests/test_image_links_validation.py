"""Тест проверки соответствия количества ссылок на изображения в MD файлах с количеством PNG файлов."""

import re
from pathlib import Path
from typing import List, Set

import pytest


class TestImageLinksValidation:
    """Тест для проверки соответствия ссылок на изображения и реальных PNG файлов."""

    def extract_sign_image_links(self, md_content: str) -> List[str]:
        """Извлекает ссылки на изображения из sign-image блоков.
        
        Ищет паттерн:
        ::sign-image
        ---
        src: /imageXXX.png
        sign: подпись
        ---
        ::
        
        Args:
            md_content (str): Содержимое markdown файла.
            
        Returns:
            List[str]: Список найденных ссылок на изображения (например, ['image123', 'image456']).
        """
        # Паттерн для поиска sign-image блоков с src: /imageXXX.png
        pattern = r'::sign-image\s*---\s*src:\s*/image(\d+)\.png\s*sign:.*?---\s*::'
        matches = re.findall(pattern, md_content, re.DOTALL | re.MULTILINE)
        return [f"image{match}" for match in matches]

    def count_png_files(self, output_dir: Path) -> int:
        """Подсчитывает количество PNG файлов в выходной директории.
        
        Args:
            output_dir (Path): Путь к выходной директории.
            
        Returns:
            int: Количество найденных PNG файлов.
        """
        png_files = list(output_dir.glob("**/*.png"))
        return len(png_files)

    def collect_all_sign_image_links(self, output_dir: Path) -> Set[str]:
        """Собирает все ссылки на изображения из всех MD файлов в выходной директории.
        
        Args:
            output_dir (Path): Путь к выходной директории.
            
        Returns:
            Set[str]: Множество уникальных ссылок на изображения.
        """
        all_links = set()
        
        # Найти все .md файлы
        md_files = list(output_dir.glob("**/*.md"))
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                links = self.extract_sign_image_links(content)
                all_links.update(links)
            except Exception as e:
                # Логируем ошибку, но не прерываем тест
                print(f"Ошибка чтения файла {md_file}: {e}")
                continue
        
        return all_links

    def test_image_links_count_matches_png_files(self):
        """Тест проверки соответствия количества ссылок на изображения количеству PNG файлов."""
        output_dir = Path("output")
        
        # Проверяем, что выходная директория существует
        if not output_dir.exists():
            pytest.skip("Выходная директория 'output' не найдена")
        
        # Собираем все ссылки на изображения из MD файлов
        sign_image_links = self.collect_all_sign_image_links(output_dir)
        
        # Подсчитываем PNG файлы
        png_count = self.count_png_files(output_dir)
        
        # Количество уникальных ссылок на изображения
        links_count = len(sign_image_links)
        
        # Логируем результаты для информации
        print(f"\nРезультаты анализа:")
        print(f"Найдено sign-image ссылок: {links_count}")
        print(f"Найдено PNG файлов: {png_count}")
        print(f"Разница: {abs(links_count - png_count)}")
        
        if links_count > 0:
            print(f"Примеры найденных ссылок: {list(sign_image_links)[:5]}")
        
        # Основная проверка: количество ссылок должно примерно соответствовать количеству файлов
        # Допускаем небольшое расхождение (±10%) из-за возможных дубликатов или технических изображений
        max_difference = max(10, png_count * 0.1)  # Минимум 10 или 10% от количества PNG
        
        difference = abs(links_count - png_count)
        
        assert difference <= max_difference, (
            f"Количество ссылок на изображения ({links_count}) значительно отличается "
            f"от количества PNG файлов ({png_count}). Разница: {difference}, "
            f"допустимая разница: {max_difference}"
        )

    def test_sign_image_pattern_extraction(self):
        """Тест проверки корректности извлечения ссылок из sign-image блоков."""
        test_content = """
        Какой-то текст до блока.
        
        ::sign-image
        ---
        src: /image123.png
        sign: Описание первого изображения
        ---
        ::
        
        Текст между блоками.
        
        ::sign-image
        ---
        src: /image456.png
        sign: Описание второго изображения с несколькими строками
        и переносами
        ---
        ::
        
        Текст после блоков.
        """
        
        links = self.extract_sign_image_links(test_content)
        
        expected_links = ["image123", "image456"]
        assert links == expected_links, f"Ожидалось {expected_links}, получено {links}"

    def test_no_false_positives_in_pattern(self):
        """Тест проверки, что паттерн не находит ложные совпадения."""
        test_content = """
        ![Image image123](path/to/image123.png)
        
        Обычная ссылка: /image999.png
        
        ::sign-image
        ---
        src: /image789.png
        sign: Это правильный блок
        ---
        ::
        
        Неправильный блок без закрывающих ::
        ::sign-image
        ---
        src: /image000.png
        sign: описание
        ---
        """
        
        links = self.extract_sign_image_links(test_content)
        
        # Должна найтись только одна правильная ссылка
        expected_links = ["image789"]
        assert links == expected_links, f"Ожидалось {expected_links}, получено {links}"

    @pytest.mark.parametrize("test_dir", [
        "output/Rrm-admin",
        "output/Dev-portal-user",
    ])
    def test_specific_directory_image_consistency(self, test_dir):
        """Параметризованный тест для проверки конкретных директорий."""
        test_path = Path(test_dir)
        
        if not test_path.exists():
            pytest.skip(f"Тестовая директория {test_dir} не найдена")
        
        # Собираем ссылки и файлы только в этой директории
        sign_image_links = self.collect_all_sign_image_links(test_path)
        png_count = self.count_png_files(test_path)
        
        links_count = len(sign_image_links)
        
        print(f"\nАнализ {test_dir}:")
        print(f"Sign-image ссылок: {links_count}")
        print(f"PNG файлов: {png_count}")
        
        # Для конкретной директории допускаем меньшее расхождение
        max_difference = max(5, png_count * 0.05)  # 5% или минимум 5
        difference = abs(links_count - png_count)
        
        assert difference <= max_difference, (
            f"В {test_dir}: количество ссылок ({links_count}) не соответствует "
            f"количеству PNG файлов ({png_count}). Разница: {difference}"
        )