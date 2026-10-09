# awesomeUI

Набор переиспользуемых UI-компонентов для PySide6 и SwiftUI, собранный из
практических компонентов GoldenNugget и упрощённых standalone-виджетов.

Цель проекта — брать готовый компонент целиком и подключать его в новый проект
без зависимости от бизнес-логики GoldenNugget.

## Возможности

- PySide6: карточки, бейджи статуса, поиск с debounce, loading-кнопки,
  empty state и toast-уведомления.
- SwiftUI: карточки, бейджи статуса, поле поиска, empty state, async-кнопки и
  toast-модификатор.
- Исходники виджетов не импортируют модули приложения GoldenNugget.
- Компоненты используют системные возможности фреймворков и не требуют
  сторонних UI-библиотек.

## Структура

```text
src/
├── widgets/
│   ├── pyside6_widgets.py          # standalone PySide6-компоненты
│   ├── swiftui/ReusableWidgets.swift # standalone SwiftUI-компоненты
│   ├── README.md                   # подробные примеры виджетов
│   └── __init__.py                 # короткие импорты
├── gui/                            # перенесённые GUI-компоненты GoldenNugget
└── qt/                             # Qt-ресурсы и custom elements
styles/                             # существующие Qt-стили
```

## PySide6

Установка зависимости:

```bash
python -m pip install PySide6
```

Минимальный пример:

```python
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from src.widgets import Card, LoadingButton, SearchField, StatusBadge, Toast

app = QApplication([])
window = QWidget()
layout = QVBoxLayout(window)

card = Card("Library", "Reusable PySide6 components")
card.add_widget(SearchField("Filter items…"))
card.add_widget(StatusBadge("Ready", "success"))

save = LoadingButton("Save")
save.clickedWhileReady.connect(lambda: save.set_loading(True))
layout.addWidget(card)
layout.addWidget(save)

window.resize(420, 260)
window.show()
app.exec()
```

Для подробного API и дополнительных примеров см. [src/widgets/README.md](src/widgets/README.md).

## SwiftUI

Добавьте `src/widgets/swiftui/ReusableWidgets.swift` в target приложения и
используйте компоненты напрямую:

```swift
import SwiftUI

struct ContentView: View {
    @State private var query = ""
    @State private var notice: String?

    var body: some View {
        WidgetCard(title: "Library", subtitle: "Reusable SwiftUI components") {
            SearchField($query)
            StatusBadge("Ready", kind: .success)
        }
        .padding()
        .toast($notice)
    }
}
```

SwiftUI-часть рассчитана на современные версии SwiftUI, где доступны
`ContentUnavailableView`, `Material` и structured concurrency.

## Принципы использования

1. Копируйте только нужный файл или каталог `src/widgets`.
2. Не смешивайте standalone-виджеты с application-specific страницами из
   `src/gui` без необходимости.
3. Переопределяйте цвета и размеры на уровне проекта, если нужен собственный
   дизайн-системный слой.

## Лицензия

См. [LICENSE](LICENSE).

