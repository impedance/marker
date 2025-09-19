проблема с форматированием картинок одном из документов, посмотри мой диалог с другой нейронкой, может поймешь что нужо сделать

@out-test/rukovodadminis31eks-monit-2.3.0/0 посмотри на документ, в нем "Меню страниц" было 
  оформлено как команда в баш терминале, проверь конвертацию и документ 
  @docs-work/rukovod_adminis_31eks-_monit-2.3.0.docx через xml парсер, почему так произошло, 
  ничего не придумыай елси не знаешь

● Я проверю документ и его конвертацию. Сначала посмотрю на результат конвертации, а затем
  проанализирую исходный документ через XML парсер.

● Search(pattern: "Меню страниц", path: "out-test/rukovodadminis31eks-monit-2.3.0",
        output_mode: "content")
  ⎿  Found 23 lines (ctrl+r to expand)

● Вижу проблему! "Меню страниц" было неправильно распознано как блок кода bash. Теперь
  проанализирую исходный DOCX документ через XML парсер.

● Bash(python -c "
      import zipfile…)
  ⎿  Error: /bin/bash: line 44: python: command not found

● Bash(source .venv/bin/activate && python -c "
      import zipfile…)
  ⎿ Найден параграф 622 с текстом: Меню страниц                                             
    XML структура параграфа:
    <ns0:p xmlns:ns0="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:ns
    … +30 lines (ctrl+r to expand)


● Отлично! Теперь вижу проблему. Проверим, как обрабатывается стиль "ROSA4" в нашем парсере:

● Bash(source .venv/bin/activate && python -c "
      import zipfile…)
  ⎿ Найден стиль ROSA4:                                                                     
    <ns0:style xmlns:ns0="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ns0:
    type="paragraph" ns0:customStyle="1" ns0:styleId="ROSA4"><ns0:name ns0:val="ROSA_Заголов
    … +10 lines (ctrl+r to expand)



● Теперь посмотрим, как обрабатывается этот стиль в нашем коде:

● Search(pattern: "ROSA4|ROSA_Заголовок", path: "core", output_mode: "content")
  ⎿  Found 7 lines (ctrl+r to expand)

● Отлично! Теперь проверим логику определения блоков кода в нашем парсере:

● Search(pattern: "code.*block|Terminal|bash", path: "core", output_mode: "content")
  ⎿  Found 190 lines (ctrl+r to expand)

● Теперь найдем функцию, которая определяет стили кода:

● Search(pattern: "is_code_style_paragraph", path: "core", output_mode: "content")
  ⎿  Found 43 lines (ctrl+r to expand)

● Теперь найдем паттерны названий стилей кода:

● Search(pattern: "code_style_name_res|CODE_STYLE_PATTERNS", path: "core", output_mode:
        "content")
  ⎿  Found 23 lines (ctrl+r to expand)

● Найдем сами паттерны:

● Search(pattern: "CODE_STYLE_NAME_PATTERNS", path: "core", output_mode: "content")
  ⎿  Found 59 lines (ctrl+r to expand)

● Теперь проверим, соответствует ли стиль "ROSA_Заголовок 4" паттернам кода:

● Bash(source .venv/bin/activate && python -c "
      import re…)
  ⎿  Проверяем стиль: ROSA_Заголовок 4
     Паттерны стилей кода:
       .*Команда.* -> Не совпадает
     … +5 lines (ctrl+r to expand)

● Стиль заголовка не должен определяться как код по названию стиля. Проверим, есть ли у него
  серая заливка и моноширинный шрифт:

● Bash(source .venv/bin/activate && python -c "
      import zipfile…)
  ⎿  Анализируем параграф 622: "Меню страниц"
     Заливка: отсутствует
     Серая заливка: False
     … +2 lines (ctrl+r to expand)

● Хорошо, теперь проверим, есть ли проблема в логике определения заголовков:

● Bash(source .venv/bin/activate && python -c "
      import zipfile…)
  ⎿  Параграф 622: "Меню страниц"    
     Стиль ID: ROSA4
     Название стиля: ROSA_Заголовок 4
     … +2 lines (ctrl+r to expand)

● Отлично! Теперь понятно, что происходит. Параграф "Меню страниц" правильно определяется как
   заголовок 4-го уровня по паттерну .*Заголовок\s*(\d)$. Но почему же он попадает в блок
  кода? Давайте проследим логику в парсере:

● Read(core/adapters/docx_parser.py)
  ⎿  Read 100 lines (ctrl+r to expand)

● Read(core/adapters/docx_parser.py)
  ⎿  Read 50 lines (ctrl+r to expand)

● Теперь найдем основную логику обработки параграфов:

● Read(core/adapters/docx_parser.py)
  ⎿  Read 100 lines (ctrl+r to expand)

● Теперь посмотрим на начало основной логики:

● Read(core/adapters/docx_parser.py)
  ⎿  Read 70 lines (ctrl+r to expand)

● Вот проблема! Теперь я вижу последовательность обработки:

  1. Строка 1037: if is_code_style_paragraph(p): - проверяется, является ли параграф стилем
  кода
  2. Только потом на строке 1091 проверяется if lvl: - является ли параграф заголовком

  Проблема в том, что проверка стиля кода идет РАНЬШЕ проверки заголовка!

  Хотя "Меню страниц" НЕ определяется как стиль кода (мы это проверили), давайте убедимся еще
   раз в функции _should_reorder_command_before_image:

● Search(pattern: "_should_reorder_command_before_image", path: "core", output_mode: "content")
  ⎿  Found 63 lines (ctrl+r to expand)

● Теперь найдем полную функцию и проверим паттерны команд:

● Search(pattern: "def _should_reorder_command_before_image", path: "core", output_mode:
        "content")
  ⎿  Found 31 lines (ctrl+r to expand)

● ВОТ ОНА, ПРОБЛЕМА! Смотрите на строки выше - есть очень широкий паттерн для "команд":

  r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s+[a-zA-Z0-9_\.-]+\s*$'  # Command with argument

  Этот паттерн может совпадать с "Меню страниц"! Проверим:

● Bash(source .venv/bin/activate && python -c "
      import re…)
  ⎿ Проверяем текст: "Меню страниц"                                                         
    Паттерны команд:
      1. ^\s*(sudo\s+)?(docker|wget|curl|psql|createdb|apt|apt-get|dnf|systemctl|sh\b|touch|
    … +9 lines (ctrl+r to expand)


● НАЙДЕНО! Вот причина проблемы:

  Паттерн r'^\s*[\w\.-]+\s+[\w\.-]+\s*$' в функции _should_reorder_command_before_image
  ошибочно определяет "Меню страниц" как команду!

  Этот паттерн слишком широкий и захватывает любой текст из двух слов, разделенных пробелом,
  что может быть обычным текстом заголовка.

  Проблема в коде core/adapters/docx_parser.py:708 - слишком общий паттерн для определения
  команд в функции _should_reorder_command_before_image.

  Текст "Меню страниц" неправильно классифицируется как команда, которая должна быть
  перемещена перед изображением и оформлена как блок кода bash с заголовком "Terminal".

  Решение: Нужно сделать паттерн более специфичным, чтобы он не захватывал обычные заголовки
  на русском языке.
