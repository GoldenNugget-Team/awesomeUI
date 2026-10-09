# Reusable widgets

These components are intentionally independent from the GoldenNugget application.
Copy the Python file or the Swift file into another project and use the public
types directly.

## PySide6

```python
from src.widgets.pyside6_widgets import Card, LoadingButton, SearchField, Toast

search = SearchField("Filter items…")
search.searchChanged.connect(lambda value: print(value))

button = LoadingButton("Save")
button.clickedWhileReady.connect(lambda: button.set_loading(True))

card = Card("Profile", "Reusable without an app theme")
card.add_widget(search)
Toast.show_message(window, "Saved")
```

The module only requires PySide6 and uses no application-specific imports.

## SwiftUI

```swift
@State private var query = ""
@State private var notice: String?

var body: some View {
    WidgetCard(title: "Library", subtitle: "Reusable SwiftUI components") {
        SearchField($query)
        StatusBadge("Ready", kind: .success)
    }
    .toast($notice)
}
```

`ReusableWidgets.swift` targets modern SwiftUI and uses `ContentUnavailableView`,
`Material`, and structured concurrency. Keep the file in the same target as the app.

