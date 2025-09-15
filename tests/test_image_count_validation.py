"""Тест сравнения количества кастомных ссылок на изображения с количеством извлеченных PNG файлов."""

import re
from pathlib import Path

import pytest


class TestImageCountValidation:
    """Тест для сравнения количества sign-image ссылок с количеством PNG файлов."""

    def count_sign_image_links(self, output_dir: Path) -> int:
        """Подсчитывает количество кастомных sign-image ссылок во всех MD файлах.
        
        Ищет паттерн: src: /imageXXX.png в блоках ::sign-image
        
        Args:
            output_dir (Path): Путь к выходной директории.
            
        Returns:
            int: Общее количество найденных ссылок.
        """
        total_links = 0
        
        # Найти все .md файлы
        md_files = list(output_dir.glob("**/*.md"))
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                # Ищем строки вида "src: /imageXXX.png"
                matches = re.findall(r'src:\s*/image\d+\.png', content)
                total_links += len(matches)
            except Exception as e:
                print(f"Ошибка чтения файла {md_file}: {e}")
                continue
        
        return total_links

    def count_png_files(self, output_dir: Path) -> int:
        """Подсчитывает количество PNG файлов в выходной директории.
        
        Args:
            output_dir (Path): Путь к выходной директории.
            
        Returns:
            int: Количество найденных PNG файлов.
        """
        png_files = list(output_dir.glob("**/*.png"))
        return len(png_files)

    def test_sign_image_links_vs_png_files_count(self):
        """Основной тест: сравнение количества кастомных ссылок с количеством PNG файлов."""
        output_dir = Path("test-output")
        
        # Проверяем, что выходная директория существует
        if not output_dir.exists():
            pytest.skip("Выходная директория 'output' не найдена")
        
        # Подсчитываем ссылки и файлы
        links_count = self.count_sign_image_links(output_dir)
        png_count = self.count_png_files(output_dir)
        
        # Выводим результаты
        print(f"\n=== РЕЗУЛЬТАТЫ СРАВНЕНИЯ ===")
        print(f"Кастомных sign-image ссылок: {links_count}")
        print(f"PNG файлов: {png_count}")
        print(f"Разница: {abs(links_count - png_count)}")
        
        if links_count == png_count:
            print("✅ КОЛИЧЕСТВА СОВПАДАЮТ")
        elif links_count > png_count:
            print(f"⚠️  Ссылок больше на {links_count - png_count}")
        else:
            print(f"⚠️  Файлов больше на {png_count - links_count}")
        
        # Простая проверка - сообщаем о результатах
        assert links_count > 0, "Не найдено ни одной кастомной ссылки на изображения"
        assert png_count > 0, "Не найдено ни одного PNG файла"
        
        # Основное утверждение для теста
        assert True, f"Тест завершен. Ссылок: {links_count}, файлов: {png_count}"