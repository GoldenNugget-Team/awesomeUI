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

### Sidebar

```python
from src.widgets import Sidebar, SidebarTheme

sidebar = Sidebar(theme=SidebarTheme(background="#101418", active_indicator="#7aa2ff"))
sidebar.add_section("Menu")
sidebar.add_item("home", "Home", icon=home_icon)
sidebar.add_item("downloads", "Downloads", icon=dl_icon, badge="3")

sidebar.add_group("ios", "iOS", icon=iphone_icon)
sidebar.add_item("posterboard", "Posterboard", group="ios")

sidebar.add_stretch()
sidebar.add_footer_widget(user_card)

sidebar.itemClicked.connect(lambda item_id: print(item_id))
sidebar.toggle_collapsed()          # animated icon-only mode
sidebar.set_expands_on_hover(True)  # expand while collapsed on hover
sidebar.with_theme(width=280, item_radius=10)
```

Everything visual goes through `SidebarTheme` (colors, sizes, radius, widths,
animation duration). Items support icons, badges, exclusive selection and
groups; the footer slot accepts any widget.


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

