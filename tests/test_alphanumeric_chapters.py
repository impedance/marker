"""
Tests for alphanumeric chapter numbering support (like Б.1, Приложение Б).

This module tests the functionality to handle documents with mixed numbering schemes
including alphabetic prefixes like "Б.1", "Приложение Б" etc.
"""
import pytest

from core.output.file_naming import chapter_index_from_h1, generate_chapter_filename
from core.utils.text_processing import (
    extract_heading_number_and_title, 
    extract_letter_index, 
    clean_heading_text
)


class TestAlphanumericHeadingRecognition:
    """Test recognition of alphabetic + numeric heading patterns."""
    
    def test_cyrillic_letter_number_pattern(self):
        """Test recognition of Cyrillic letter.number patterns."""
        assert extract_heading_number_and_title("Б.1 Протоколы") == ("Б.1", "Протоколы")
        assert extract_heading_number_and_title("В.2.1 Детали протокола") == ("В.2.1", "Детали протокола")
        assert extract_heading_number_and_title("Г.3 Элементы данных") == ("Г.3", "Элементы данных")
        assert extract_heading_number_and_title("Д.1.2.3 Подробности") == ("Д.1.2.3", "Подробности")
    
    def test_appendix_patterns(self):
        """Test recognition of 'Приложение X' patterns."""
        assert extract_heading_number_and_title("Приложение А. Конфигурация") == ("Приложение А", "Конфигурация")
        assert extract_heading_number_and_title("Приложение Б Протоколы") == ("Приложение Б", "Протоколы")
        assert extract_heading_number_and_title("Приложение В. Типы процессов") == ("Приложение В", "Типы процессов")
        assert extract_heading_number_and_title("Приложение Г  Элементы данных") == ("Приложение Г", "Элементы данных")
    
    def test_latin_letter_patterns(self):
        """Test recognition of Latin letter patterns."""
        assert extract_heading_number_and_title("A.1 Configuration") == ("A.1", "Configuration")
        assert extract_heading_number_and_title("B.2.1 Protocol Details") == ("B.2.1", "Protocol Details")
        assert extract_heading_number_and_title("Appendix C Implementation") == ("Appendix C", "Implementation")
    
    def test_mixed_case_patterns(self):
        """Test patterns with mixed case handling."""
        assert extract_heading_number_and_title("б.1 Нижний регистр") == ("б.1", "Нижний регистр")
        assert extract_heading_number_and_title("ПРИЛОЖЕНИЕ А ЗАГЛАВНЫЕ") == ("ПРИЛОЖЕНИЕ А", "ЗАГЛАВНЫЕ")
    
    def test_with_separators(self):
        """Test patterns with various separators."""
        assert extract_heading_number_and_title("Б.1 — Протоколы с тире") == ("Б.1", "Протоколы с тире")
        assert extract_heading_number_and_title("В.2 – Протоколы с дефисом") == ("В.2", "Протоколы с дефисом")
        assert extract_heading_number_and_title("Г.3. Протоколы с точкой") == ("Г.3", "Протоколы с точкой")


class TestLetterIndexExtraction:
    """Test extraction of numeric indices from alphabetic patterns."""
    
    def test_cyrillic_letter_extraction(self):
        """Test extracting indices from Cyrillic letters."""
        assert extract_letter_index("Б.1") == 2  # Б is 2nd letter
        assert extract_letter_index("В.2.3") == 3  # В is 3rd letter  
        assert extract_letter_index("Г.3") == 4  # Г is 4th letter
        assert extract_letter_index("Д.1") == 5  # Д is 5th letter
        assert extract_letter_index("А.10") == 1  # А is 1st letter
    
    def test_appendix_extraction(self):
        """Test extracting indices from Приложение patterns."""
        assert extract_letter_index("Приложение А") == 1
        assert extract_letter_index("Приложение Б") == 2
        assert extract_letter_index("Приложение В") == 3
        assert extract_letter_index("Приложение Г") == 4
    
    def test_latin_letter_extraction(self):
        """Test extracting indices from Latin letters."""
        assert extract_letter_index("A.1") == 1
        assert extract_letter_index("B.2") == 2
        assert extract_letter_index("C.3") == 3
        assert extract_letter_index("Appendix B") == 2
    
    def test_no_letter_cases(self):
        """Test cases without alphabetic patterns."""
        assert extract_letter_index("1.2") == 0  # No letter
        assert extract_letter_index("123") == 0  # No letter
        assert extract_letter_index("") == 0  # Empty
        assert extract_letter_index("Introduction") == 0  # Plain text


class TestAlphanumericFileNaming:
    """Test file naming for alphanumeric chapters."""
    
    def test_cyrillic_letter_index_extraction(self):
        """Test extracting sort index from Cyrillic letter patterns."""
        assert chapter_index_from_h1("Б.1 Протоколы") == 2  # Б is 2nd letter
        assert chapter_index_from_h1("В.2 Типы") == 3       # В is 3rd letter
        assert chapter_index_from_h1("Г.3 Элементы") == 4   # Г is 4th letter
        assert chapter_index_from_h1("Д.1 Данные") == 5     # Д is 5th letter
    
    def test_appendix_index_extraction(self):
        """Test extracting sort index from Приложение patterns."""
        assert chapter_index_from_h1("Приложение А. Конфигурация") == 1
        assert chapter_index_from_h1("Приложение Б Протоколы") == 2
        assert chapter_index_from_h1("Приложение В Типы") == 3
        assert chapter_index_from_h1("Приложение Г Элементы") == 4
    
    def test_latin_letter_index_extraction(self):
        """Test extracting sort index from Latin letter patterns."""
        assert chapter_index_from_h1("A.1 Configuration") == 1
        assert chapter_index_from_h1("B.2 Protocols") == 2
        assert chapter_index_from_h1("C.3 Types") == 3
    
    def test_generate_alphanumeric_filenames(self):
        """Test generating filenames for alphanumeric chapters."""
        # Should use extracted letter position for sorting
        result = generate_chapter_filename(99, "Б.1 Протоколы")
        assert result.startswith("02-")  # Б = 2
        assert "protokoly" in result.lower() or "протоколы" in result.lower()
        
        result = generate_chapter_filename(99, "Приложение В Типы процессов")
        assert result.startswith("03-")  # В = 3
        assert "tipy" in result.lower() or "типы" in result.lower()
        
        result = generate_chapter_filename(99, "Г.3.4 Получение списка")
        assert result.startswith("04-")  # Г = 4
        assert "poluchenie" in result.lower() or "получение" in result.lower()
    
    def test_fallback_for_unsupported_letters(self):
        """Test fallback behavior for unsupported letters."""
        # Letters beyond typical appendix range but still in alphabet
        result = generate_chapter_filename(10, "Я.1 Последняя буква")
        assert result.startswith("33-")  # Я = 33rd letter in Cyrillic alphabet
    
    def test_mixed_document_numbering(self):
        """Test handling documents with mixed numbering schemes."""
        # Should handle both numeric and alphabetic chapters
        numeric_result = generate_chapter_filename(1, "1 Введение")
        alpha_result = generate_chapter_filename(99, "Б.1 Протоколы")
        
        assert numeric_result.startswith("01-")
        assert alpha_result.startswith("02-")


class TestCleanHeadingText:
    """Test cleaning of heading text to remove numbering prefixes."""
    
    def test_numeric_cleaning(self):
        """Test cleaning of numeric prefixes."""
        assert clean_heading_text("1 Введение") == "Введение"
        assert clean_heading_text("2.1 Архитектура") == "Архитектура"
        assert clean_heading_text("3.4.5 — Конфигурация") == "Конфигурация"
    
    def test_alphabetic_cleaning(self):
        """Test cleaning of alphabetic prefixes."""
        assert clean_heading_text("Б.1 Протоколы") == "Протоколы"
        assert clean_heading_text("Приложение А. Конфигурация демонов") == "Конфигурация демонов"
        assert clean_heading_text("В.2.3 Детали реализации") == "Детали реализации"
        assert clean_heading_text("A.1 Configuration") == "Configuration"
        assert clean_heading_text("Appendix B Implementation") == "Implementation"
    
    def test_mixed_patterns(self):
        """Test cleaning of various mixed patterns."""
        assert clean_heading_text("Г.3.3 — Получение списка") == "Получение списка"
        assert clean_heading_text("Приложение Д  Типы элементов") == "Типы элементов"
        assert clean_heading_text("Е.1. Пользовательские команды") == "Пользовательские команды"
    
    def test_no_numbering(self):
        """Test text without numbering prefixes."""
        assert clean_heading_text("Заключение") == "Заключение"
        assert clean_heading_text("Общие сведения") == "Общие сведения"
        assert clean_heading_text("Introduction") == "Introduction"


class TestIntegrationWithRealPatterns:
    """Integration tests using patterns from real documents."""
    
    def test_real_document_patterns(self):
        """Test patterns found in the analyzed document."""
        real_patterns = [
            ("Приложение А. Конфигурация демонов", "Приложение А", "Конфигурация демонов"),
            ("Приложение Б. Протоколы", "Приложение Б", "Протоколы"),
            ("Б.1 Активный прокси", "Б.1", "Активный прокси"),
            ("Приложение В. Типы процессов", "Приложение В", "Типы процессов"),
            ("Приложение Г. Элементы данных", "Приложение Г", "Элементы данных"),
            ("Г.3.3 Получение списка активных проверок", "Г.3.3", "Получение списка активных проверок"),
            ("Г.3.4 Отправка собранных данных", "Г.3.4", "Отправка собранных данных"),
            ("Приложение Д. Типы элементов данных", "Приложение Д", "Типы элементов данных"),
            ("Д.1 Примеры использования", "Д.1", "Примеры использования"),
            ("Приложение Е. Пользовательские команды", "Приложение Е", "Пользовательские команды")
        ]
        
        for full_text, expected_number, expected_title in real_patterns:
            number, title = extract_heading_number_and_title(full_text)
            assert number == expected_number, f"Failed for: {full_text}"
            assert title == expected_title, f"Failed for: {full_text}"
            
            # Test filename generation
            filename = generate_chapter_filename(1, full_text)
            assert filename.endswith(".md")
            assert len(filename) > 0
            
            # Test cleaning
            clean = clean_heading_text(full_text)
            assert clean == expected_title, f"Cleaning failed for: {full_text}"
    
    def test_chapter_index_extraction_real(self):
        """Test chapter index extraction with real patterns."""
        test_cases = [
            ("Приложение А. Конфигурация демонов", 1),
            ("Приложение Б. Протоколы", 2), 
            ("Б.1 Активный прокси", 2),
            ("Приложение В. Типы процессов", 3),
            ("Приложение Г. Элементы данных", 4),
            ("Г.3.3 Получение списка", 4),
            ("Приложение Д. Типы элементов данных", 5),
            ("Д.1 Примеры использования", 5),
            ("Приложение Е. Пользовательские команды", 6)
        ]
        
        for heading, expected_index in test_cases:
            actual_index = chapter_index_from_h1(heading)
            assert actual_index == expected_index, f"Index extraction failed for: {heading}"


class TestBackwardCompatibility:
    """Test that existing numeric functionality still works."""
    
    def test_numeric_patterns_still_work(self):
        """Ensure numeric patterns still work after changes."""
        assert extract_heading_number_and_title("1 Введение") == ("1", "Введение")
        assert extract_heading_number_and_title("2.1 Архитектура") == ("2.1", "Архитектура")
        assert extract_heading_number_and_title("3.4.5 — Детали") == ("3.4.5", "Детали")
        
        assert chapter_index_from_h1("1 Введение") == 1
        assert chapter_index_from_h1("2.1 Архитектура") == 2
        assert chapter_index_from_h1("10.3 Глава десять") == 10
        
        assert clean_heading_text("1 Введение") == "Введение"
        assert clean_heading_text("2.1 Архитектура") == "Архитектура"
    
    def test_mixed_documents(self):
        """Test handling documents with both numeric and alphabetic numbering."""
        patterns = [
            "1 Введение",
            "2 Архитектура", 
            "3 Реализация",
            "Приложение А. Конфигурация",
            "Приложение Б. Протоколы",
            "Б.1 Активный прокси"
        ]
        
        indices = [chapter_index_from_h1(p) for p in patterns]
        
        # Should extract: 1, 2, 3, 1, 2, 2
        assert indices == [1, 2, 3, 1, 2, 2]
        
        # All should have clean titles
        titles = [clean_heading_text(p) for p in patterns]
        expected_titles = [
            "Введение", "Архитектура", "Реализация",
            "Конфигурация", "Протоколы", "Активный прокси"
        ]
        assert titles == expected_titles