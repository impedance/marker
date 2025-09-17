#!/bin/bash

# Скрипт для переименования файлов Dynamic Directory
# Убирает префикс "Dynamic Directory 4.2 ", делает транслитерацию и обрезает длинные слова

# Функция транслитерации
transliterate() {
    local input="$1"
    echo "$input" | sed \
        -e 's/а/a/g' -e 's/б/b/g' -e 's/в/v/g' -e 's/г/g/g' -e 's/д/d/g' \
        -e 's/е/e/g' -e 's/ё/yo/g' -e 's/ж/zh/g' -e 's/з/z/g' -e 's/и/i/g' \
        -e 's/й/y/g' -e 's/к/k/g' -e 's/л/l/g' -e 's/м/m/g' -e 's/н/n/g' \
        -e 's/о/o/g' -e 's/п/p/g' -e 's/р/r/g' -e 's/с/s/g' -e 's/т/t/g' \
        -e 's/у/u/g' -e 's/ф/f/g' -e 's/х/h/g' -e 's/ц/ts/g' -e 's/ч/ch/g' \
        -e 's/ш/sh/g' -e 's/щ/shch/g' -e 's/ъ//g' -e 's/ы/y/g' -e 's/ь//g' \
        -e 's/э/e/g' -e 's/ю/yu/g' -e 's/я/ya/g' \
        -e 's/А/A/g' -e 's/Б/B/g' -e 's/В/V/g' -e 's/Г/G/g' -e 's/Д/D/g' \
        -e 's/Е/E/g' -e 's/Ё/Yo/g' -e 's/Ж/Zh/g' -e 's/З/Z/g' -e 's/И/I/g' \
        -e 's/Й/Y/g' -e 's/К/K/g' -e 's/Л/L/g' -e 's/М/M/g' -e 's/Н/N/g' \
        -e 's/О/O/g' -e 's/П/P/g' -e 's/Р/R/g' -e 's/С/S/g' -e 's/Т/T/g' \
        -e 's/У/U/g' -e 's/Ф/F/g' -e 's/Х/H/g' -e 's/Ц/Ts/g' -e 's/Ч/Ch/g' \
        -e 's/Ш/Sh/g' -e 's/Щ/Shch/g' -e 's/Ъ//g' -e 's/Ы/Y/g' -e 's/Ь//g' \
        -e 's/Э/E/g' -e 's/Ю/Yu/g' -e 's/Я/Ya/g'
}

# Функция поиска последней согласной в слове
find_last_consonant() {
    local word="$1"
    local consonants="bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ"
    
    # Идем с конца слова и ищем согласную
    for ((i=${#word}-1; i>=0; i--)); do
        char="${word:$i:1}"
        if [[ "$consonants" == *"$char"* ]]; then
            echo $((i+1))
            return
        fi
    done
    echo ${#word}
}

# Функция обрезки слов с учетом позиции: первые два до 7 букв, остальные до 5
trim_long_words() {
    local input="$1"
    local result=""
    local word_count=0
    
    # Разбиваем на слова, обрабатываем каждое
    for word in $input; do
        ((word_count++))
        
        # Убираем знаки препинания для обработки
        clean_word=$(echo "$word" | sed 's/[^a-zA-Z0-9]//g')
        punctuation=$(echo "$word" | sed 's/[a-zA-Z0-9]//g')
        
        # Определяем максимальную длину в зависимости от позиции слова
        local max_length
        if [[ $word_count -le 2 ]]; then
            max_length=7
        else
            max_length=5
        fi
        
        if [[ ${#clean_word} -gt $max_length ]]; then
            # Ищем последнюю согласную для обрезки
            pos=$(find_last_consonant "$clean_word")
            if [[ $pos -le $max_length ]]; then
                # Если согласная в пределах максимальной длины, берем ее
                trimmed="${clean_word:0:$pos}"
            else
                # Иначе обрезаем на максимальной длине и ищем согласную назад
                short="${clean_word:0:$max_length}"
                pos=$(find_last_consonant "$short")
                trimmed="${clean_word:0:$pos}"
            fi
            result="$result ${trimmed}${punctuation}"
        else
            result="$result $word"
        fi
    done
    
    echo "$result" | sed 's/^ *//'
}

# Функция полной обработки имени файла
process_filename() {
    local filename="$1"
    
    # Убираем префикс "Dynamic Directory 4.2 "
    local without_prefix
    if [[ "$filename" =~ ^"Dynamic Directory 4.2 "(.*)$ ]]; then
        without_prefix="${BASH_REMATCH[1]}"
    else
        without_prefix="$filename"
    fi
    
    # Разделяем на имя и расширение
    local basename="${without_prefix%.*}"
    local extension="${without_prefix##*.}"
    
    # Транслитерируем основную часть
    local transliterated=$(transliterate "$basename")
    
    # Обрезаем длинные слова
    local trimmed=$(trim_long_words "$transliterated")
    
    # Заменяем пробелы и точки на подчеркивания, убираем лишние символы
    local cleaned=$(echo "$trimmed" | sed 's/[. ]/_/g' | sed 's/__*/_/g' | sed 's/^_//; s/_$//')
    
    # Приводим к нижнему регистру
    cleaned=$(echo "$cleaned" | tr '[:upper:]' '[:lower:]')
    
    echo "${cleaned}.${extension}"
}

# Основная функция переименования
rename_files() {
    local dir="/home/spec/work/rosa/marker/real-docs/dd"
    
    echo "Переименование файлов в директории: $dir"
    echo "========================================="
    
    cd "$dir" || exit 1
    
    # Обрабатываем все .docx файлы
    for file in *.docx; do
        if [[ -f "$file" ]]; then
            new_name=$(process_filename "$file")
            
            echo "Переименовываю:"
            echo "  ИЗ: $file"
            echo "  В:  $new_name"
            echo
            
            # Проверяем, что новое имя не существует
            if [[ -f "$new_name" ]]; then
                echo "ВНИМАНИЕ: Файл $new_name уже существует!"
                echo "Добавляю суффикс..."
                counter=1
                name_part="${new_name%.docx}"
                while [[ -f "${name_part}_${counter}.docx" ]]; do
                    ((counter++))
                done
                new_name="${name_part}_${counter}.docx"
                echo "Новое имя: $new_name"
                echo
            fi
            
            # Выполняем переименование
            mv "$file" "$new_name"
        fi
    done
    
    echo "Переименование завершено!"
    echo "Результат:"
    ls -la *.docx
}

# Функция предварительного просмотра (без реального переименования)
preview_rename() {
    local dir="/home/spec/work/rosa/marker/real-docs/dd"
    
    echo "ПРЕДВАРИТЕЛЬНЫЙ ПРОСМОТР переименования файлов Dynamic Directory:"
    echo "================================================================="
    
    cd "$dir" || exit 1
    
    for file in *.docx; do
        if [[ -f "$file" ]]; then
            new_name=$(process_filename "$file")
            echo "$file → $new_name"
        fi
    done
}

# Функция возврата к оригинальным именам
restore_original_names() {
    local dir="/home/spec/work/rosa/marker/real-docs/dd"
    
    echo "Восстановление оригинальных имен файлов Dynamic Directory:"
    echo "========================================================="
    
    cd "$dir" || exit 1
    
    # Создаем мапинг для восстановления имен
    declare -A restore_map=(
        ["opisan_prog.docx"]="Dynamic Directory 4.2 Описание программы.docx"
        ["poyas_zapis_zhizn_tsikl.docx"]="Dynamic Directory 4.2 Пояснительная записка. Жизненный цикл.docx"
        ["ra_chast_1_ust_i_nastr.docx"]="Dynamic Directory 4.2 РА. Часть 1. Установка и настройка.docx"
        ["ra_chast_2_ekspl.docx"]="Dynamic Directory 4.2 РА. Часть 2. Эксплуатация.docx"
        ["ra_chast_3_priloz.docx"]="Dynamic Directory 4.2 РА. Часть 3. Приложения.docx"
    )
    
    for current_name in "${!restore_map[@]}"; do
        if [[ -f "$current_name" ]]; then
            original_name="${restore_map[$current_name]}"
            echo "Восстанавливаю: $current_name → $original_name"
            mv "$current_name" "$original_name"
        fi
    done
    
    echo "Восстановление завершено!"
}

# Главное меню
case "${1:-preview}" in
    "preview"|"p")
        preview_rename
        ;;
    "rename"|"r")
        rename_files
        ;;
    "restore")
        restore_original_names
        ;;
    "help"|"h")
        echo "Использование: $0 [preview|rename|restore|help]"
        echo "  preview (по умолчанию) - показать что будет переименовано"
        echo "  rename - выполнить переименование"
        echo "  restore - восстановить оригинальные имена"
        echo "  help - показать эту справку"
        ;;
    *)
        echo "Неизвестная команда: $1"
        echo "Используйте: $0 help"
        exit 1
        ;;
esac