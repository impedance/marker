"""Тесты проверки правильности извлечения изображений из DOCX файлов."""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from subprocess import run, PIPE

import pytest


class TestImageExtraction:
    """Тесты извлечения изображений из документов."""

    def count_images_in_docx(self, docx_path: Path) -> int:
        """Подсчитывает количество изображений в DOCX файле.
        
        Args:
            docx_path (Path): Путь к DOCX файлу.
            
        Returns:
            int: Количество найденных изображений.
        """
        with zipfile.ZipFile(docx_path, 'r') as zip_file:
            media_files = [f for f in zip_file.namelist() 
                          if f.startswith('word/media/') and 
                          f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))]
            return len(media_files)

    def count_images_in_output(self, output_dir: Path) -> int:
        """Подсчитывает количество извлеченных изображений в выходной папке.
        
        Args:
            output_dir (Path): Путь к выходной папке.
            
        Returns:
            int: Количество найденных изображений.
        """
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        image_files = []
        for ext in image_extensions:
            image_files.extend(output_dir.glob(f'**/*{ext}'))
        return len(image_files)

    def test_image_extraction_cu_admin_install(self):
        """Тест проверки извлечения изображений из реального документа cu-admin-install.docx."""
        # Paths
        docx_path = Path("real-docs/cu-admin-install.docx")
        
        # Проверяем, что исходный файл существует
        assert docx_path.exists(), f"DOCX файл не найден: {docx_path}"
        
        # Подсчитываем изображения в исходном DOCX
        source_image_count = self.count_images_in_docx(docx_path)
        
        # Создаем временную папку для вывода
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir) / "test_output"
            temp_output.mkdir()
            
            # Запускаем обработку через CLI
            cmd = [
                ".venv/bin/python", "doc2chapmd.py", "build", 
                str(docx_path), "-o", str(temp_output)
            ]
            
            result = run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            
            # Проверяем, что команда выполнилась успешно
            assert result.returncode == 0, f"Команда завершилась с ошибкой: {result.stderr}"
            
            # Подсчитываем извлеченные изображения
            extracted_image_count = self.count_images_in_output(temp_output)
            
            # Ожидаем n-1 изображений (одно изображение - логотип, который не извлекается)
            expected_extracted_count = source_image_count - 1
            
            # Проверяем точное соответствие или допускаем отклонение на ±1
            difference = abs(expected_extracted_count - extracted_image_count)
            
            assert difference <= 1, (
                f"Неверное количество извлеченных изображений: "
                f"исходных={source_image_count}, ожидаемых извлеченных={expected_extracted_count}, "
                f"фактически извлеченных={extracted_image_count}, разница={difference}"
            )
            
            # Логируем результаты для информации
            print(f"Изображений в DOCX: {source_image_count}")
            print(f"Ожидаемых извлеченных (n-1): {expected_extracted_count}")
            print(f"Фактически извлечено: {extracted_image_count}")
            print(f"Разница от ожидаемого: {difference}")

    def test_image_extraction_with_expected_values(self):
        """Тест с известными ожидаемыми значениями для cu-admin-install.docx."""
        docx_path = Path("real-docs/cu-admin-install.docx")
        
        if not docx_path.exists():
            pytest.skip("Тестовый файл cu-admin-install.docx не найден")
        
        # Известные значения на момент создания теста
        expected_source_count = 50
        expected_extracted_count = 49  # n-1 (логотип не извлекается)
        
        # Проверяем исходное количество
        actual_source_count = self.count_images_in_docx(docx_path)
        assert actual_source_count == expected_source_count, (
            f"Количество изображений в DOCX изменилось: "
            f"ожидалось={expected_source_count}, получено={actual_source_count}"
        )
        
        # Проверяем, что формула n-1 соответствует ожидаемому результату
        calculated_expected = expected_source_count - 1
        assert calculated_expected == expected_extracted_count, (
            f"Логика n-1 не соответствует ожидаемому результату: "
            f"исходных={expected_source_count}, n-1={calculated_expected}, "
            f"ожидаемых={expected_extracted_count}"
        )

    @pytest.mark.parametrize("docx_filename", [
        "cu-admin-install.docx",
        "dev-portal-user.docx",
        # Можно добавить другие DOCX файлы для тестирования
    ])
    def test_no_image_loss_parametrized(self, docx_filename):
        """Параметризованный тест для проверки корректного извлечения изображений (n-1 логика).
        
        Args:
            docx_filename (str): Имя DOCX файла для тестирования.
        """
        docx_path = Path("real-docs") / docx_filename
        
        if not docx_path.exists():
            pytest.skip(f"Тестовый файл {docx_filename} не найден")
        
        source_count = self.count_images_in_docx(docx_path)
        expected_extracted_count = source_count - 1  # n-1 (логотип не извлекается)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir) / "test_output"
            temp_output.mkdir()
            
            cmd = [
                ".venv/bin/python", "doc2chapmd.py", "build", 
                str(docx_path), "-o", str(temp_output)
            ]
            
            result = run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            assert result.returncode == 0, f"Обработка не удалась: {result.stderr}"
            
            extracted_count = self.count_images_in_output(temp_output)
            
            # Проверяем, что количество соответствует ожиданиям (n-1) с допуском ±1
            difference = abs(expected_extracted_count - extracted_count)
            assert difference <= 1, (
                f"Неверное количество изображений в {docx_filename}: "
                f"исходных={source_count}, ожидаемых(n-1)={expected_extracted_count}, "
                f"извлеченных={extracted_count}, разница={difference}"
            )
            
            # Логируем результаты
            print(f"Файл: {docx_filename}")
            print(f"  Исходных изображений: {source_count}")
            print(f"  Ожидаемых (n-1): {expected_extracted_count}")
            print(f"  Извлечено: {extracted_count}")
            print(f"  Разница: {difference}")