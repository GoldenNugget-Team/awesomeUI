# awesomeUI
Random widgets for pyside and swiftui

## Widgets

- PySide6: cards, status badges, debounced search, loading buttons, empty
  states, and toast notifications.
- SwiftUI: cards, status badges, search fields, empty states, async buttons,
  and a toast modifier.


## PySide6

Install the dependency:

```bash
python -m pip install PySide6
```

Example:

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

## License

See [LICENSE](LICENSE).

