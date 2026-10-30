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

## GoldenNugget UI snapshot

`src/gui`, Qt custom elements, icons, images, fonts, credits, and `styles` are
snapshots of the UI layer in GoldenNugget. They include its search and segmented
filters, collapsible sections, dialogs, restore progress, operation results,
status bar preview, and theme system. App pages and dialogs still require the
GoldenNugget backend; this repository is not a standalone GoldenNugget app.
The independent components in `src/widgets` keep their separate API.

Refresh from the sibling checkout, or choose another local checkout:

```bash
python3 scripts/sync_goldennugget.py
python3 scripts/sync_goldennugget.py --source ~/Projects/GoldenNugget
python3 scripts/sync_goldennugget.py --check
```

The sync copies current working-tree contents, records the source commit and
SHA-256 hashes in `goldennugget-ui.json`, and skips Python caches. It leaves
destination-only files in place, including the independent PySide6 and SwiftUI
widgets. `--check` verifies the source files, hashes, and resource manifest without
writing anything.

Build the bundled Qt resources before using GoldenNugget components:

```bash
pyside6-rcc src/qt/resources.qrc -o src/qt/resources_rc.py
```

Import `src.qt.resources_rc` before constructing those widgets so `:/icon/...`
and the other resource paths resolve. For example:

```python
import src.qt.resources_rc
from src.gui.ios.components import IOSCard, IOSSearchField
```

The resource manifest is generated from the synced assets. Generated resource
modules and binaries are local build outputs.

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

