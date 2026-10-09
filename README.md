# awesomeUI

A collection of reusable UI components for PySide6 and SwiftUI, built from
practical GoldenNugget components and simplified standalone widgets.

The goal is to copy a component into a new project and use it without depending
on GoldenNugget business logic.

## Features

- PySide6: cards, status badges, debounced search, loading buttons, empty
  states, and toast notifications.
- SwiftUI: cards, status badges, search fields, empty states, async buttons,
  and a toast modifier.
- Widget sources do not import GoldenNugget application modules.
- Components use framework APIs and require no third-party UI libraries.

## Structure

```text
src/
├── widgets/
│   ├── pyside6_widgets.py             # standalone PySide6 components
│   ├── swiftui/ReusableWidgets.swift  # standalone SwiftUI components
│   ├── README.md                      # widget API and examples
│   └── __init__.py                    # short Python imports
├── gui/                               # imported GoldenNugget GUI components
└── qt/                                # Qt resources and custom elements
styles/                                # existing Qt styles
```

## PySide6

Install the dependency:

```bash
python -m pip install PySide6
```

Minimal example:

```python
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from src.widgets import Card, LoadingButton, SearchField, StatusBadge

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

See [src/widgets/README.md](src/widgets/README.md) for the widget API and more examples.

## SwiftUI

Add `src/widgets/swiftui/ReusableWidgets.swift` to your app target and use the
components directly:

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

The SwiftUI components target modern SwiftUI versions with
`ContentUnavailableView`, `Material`, and structured concurrency.

## Usage principles

1. Copy only the file or directory you need from `src/widgets`.
2. Keep standalone widgets separate from the application-specific pages in
   `src/gui` unless you explicitly need those pages.
3. Override colors and dimensions at the project level when using a custom
   design system.

## License

See [LICENSE](LICENSE).

