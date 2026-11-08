import QtQuick
import qs.Ui
import qs.Commons

BarWidget {
  id: root
  moduleName: "omarchy.menu"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    hasVisualContent: true
    horizontalMargin: 12
    
    // Explicitly set the width so it doesn't collapse to 0 and overlap adjacent widgets
    fixedWidth: row.implicitWidth + (horizontalMargin * 2)

    Row {
      id: row
      anchors.centerIn: parent
      spacing: 8

      Text {
        text: "󰣇"
        font.family: root.bar ? root.bar.fontFamily : Style.font.family
        font.pixelSize: 15
        color: button.active && button.useActiveColor ? button.activeColor : button.foreground
        anchors.verticalCenter: parent.verticalCenter
      }

      Text {
        text: "X64 LIOS"
        font.family: root.bar ? root.bar.fontFamily : Style.font.family
        font.pixelSize: 13
        font.weight: Font.ExtraBold
        font.letterSpacing: 0.5
        color: button.active && button.useActiveColor ? button.activeColor : button.foreground
        anchors.verticalCenter: parent.verticalCenter
      }
    }

    onPressed: function(mouseButton) {
      if (!root.bar) return
      if (mouseButton === Qt.RightButton) root.bar.run("xdg-terminal-exec")
      else root.bar.run("omarchy-shell shell toggle omarchy.menu '{\"menu\":\"root\"}'")
    }
  }
}
