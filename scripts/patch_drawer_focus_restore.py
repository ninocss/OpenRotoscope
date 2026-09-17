from pathlib import Path

path = Path('app/openroto/ui/PolishedMain.qml')
text = path.read_text(encoding='utf-8')
old = '''        onClosed: {
            if (window.compactMode && compactControlsButton.visible)
                compactControlsButton.forceActiveFocus(Qt.TabFocusReason)
        }
'''
new = '''        onClosed: {
            if (window.compactMode && compactControlsButton.visible) {
                Qt.callLater(function() {
                    compactControlsButton.forceActiveFocus(Qt.TabFocusReason)
                })
            }
        }
'''
if old not in text:
    raise SystemExit('drawer onClosed block not found')
path.write_text(text.replace(old, new), encoding='utf-8')
